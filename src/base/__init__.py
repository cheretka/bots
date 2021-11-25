from typing import Optional, Type
from websockets.legacy.client import connect, WebSocketClientProtocol
from gameproxy import connection_proxy
from agent import Agent
import asyncio
import concurrent.futures as cf

ENV_VARS = {
	"name":"",
	"server":"",
	"session_id":"",
	"game_type":"",
	"bot_name":""
}


@connection_proxy
async def make_env(server: str, name: str, game_type: str, 
				   bot_name: str, session_id: Optional[str] =None,
				   join: bool =False) -> WebSocketClientProtocol:
	"""Makes the environment, that is, creates or joins to game based on provided server URL, name of game and session identifier

	Args:
		server (str): URL of server (local or public)
		name (str): name of game, applicable if client want to create new game
		game_type (str): type of game, in the future the type of this parameter will be changed
		bot_name (str): name of bot, that wants to join the game
		session_id (Optional[str], optional): session identifier. Defaults to None.
		join (bool, optional): Flag that indicates whether or not client want to join to existing session. Defaults to False.

	Raises:
		ValueError: if session identifier is empty as long as client wanted to join the game.

	Returns:
		WebSocketClientProtocol: Obtained connection
	"""
	if join:
		if not session_id: 
			raise ValueError("Provided session identifier is empty, if you want to join to exisiting game, provide valid session id")
		url = f"{server}/join_to_game?player_name={bot_name}&session_id={session_id}"
		socket = await connect(url)
  
		ENV_VARS["game_type"] = game_type
		ENV_VARS["name"] = name
		ENV_VARS["server"] = server
		ENV_VARS["session_id"] = session_id
		ENV_VARS["bot_name"] = bot_name
  
		return socket
	else:
		url = f"{server}/create_game?name={name}&type={game_type}"
		async with connect(url) as web_socket:
			session_id = await web_socket.recv()
			await asyncio.sleep(0)
			return await make_env(server, name, game_type, bot_name, session_id, True)

def __run_bot(random_bot_class: Type[Agent], server: str, session_id: str, int_id: int, **agent_kwds):
	"""Helper function for bot execution

	Args:
		random_bot_class (Type[Agent]): Agent initializer
		server (str): server URL
		session_id (str): session identifier
		int_id (int): identifier of bot object
	"""
    
	url = f"{server}/join_to_game?player_name={random_bot_class.__name__}_{int_id}&session_id={session_id}"
	loop = asyncio.get_event_loop()
 
	async def wrapper():
		"""Wrapper for networking tasks execution during bot interaction with game.
		"""
		_ = await connection_proxy(connect(url))
		bot = random_bot_class(**agent_kwds)
  
		async def bot_loop():
			"""Bot behaviour
			"""
			done = False
			while not done:
				_ = bot.choose_action()
				done = bot.is_dead
				await asyncio.sleep(0.1)
    
		acting_task = asyncio.ensure_future(bot_loop())
		receive_task = asyncio.ensure_future(bot.handle_new_states())
		_, pending = await asyncio.wait([receive_task, acting_task], return_when=asyncio.FIRST_COMPLETED)
		for task in pending: task.cancel()
  
	loop.run_until_complete(wrapper)
	
def spawn_random_bots(server: str, session_id: str, random_bot_class: Type[Agent], count: int, **agent_kwds):
	"""Spawns some random bots on server 

	Args:
		server (str): URL of target server
		session_id (str): session identifier of game
		random_bot_class (Type): initializer of bot objects
		count (int): count of bots to spawn
		agent_kwds: agent's constructor parameters
	"""
	with cf.ProcessPoolExecutor(max_workers=count) as executor:
		_futures = {num: executor.submit(__run_bot, random_bot_class, server, session_id, num, **agent_kwds) for num in range(count)}
		for num, future in (_futures.items()): future.add_done_callback(lambda: print(f"Process of bot No. {num} is finished"))
  