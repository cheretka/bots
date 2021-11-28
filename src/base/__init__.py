from concurrent.futures.thread import ThreadPoolExecutor
from socket import socket
from typing import Optional, Type
import logging
from websockets.legacy.client import connect, WebSocketClientProtocol
from ._gameproxy import connection_proxy as __connection_proxy
from .agent import Agent
from .action import Action
import asyncio
import concurrent.futures as cf
from time import sleep
logger = logging.getLogger(__name__) 

__ENV_VARS = {
	"name":"",
	"server":"",
	"session_id":"",
	"game_type":"",
	"bot_name":""
}

def get_session_id(): return __ENV_VARS["session_id"]


def make_env(server: str, name: str, game_type: str, 
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
	

	socket = __make_env(server, name, game_type, bot_name, session_id, join)
	
	print(f"Established connection at: {socket.host}")
  
@__connection_proxy
async def __make_env(server: str, name: str, game_type: str, 
				   bot_name: str, session_id: Optional[str] =None,
				   join: bool =False) -> WebSocketClientProtocol:
    
	__ENV_VARS["game_type"] = game_type
	__ENV_VARS["name"] = name
 
	if not join:
		url = f"{server}/create_game?name={name}&type={game_type}"
		async with connect(url) as web_socket:
			session_id = await web_socket.recv()
			await asyncio.sleep(0)
	
			
	return await __join(server, session_id, bot_name)

async def __join(server: str, session_id: str, bot_name: str):
	if not session_id: 
		raise ValueError("Provided session identifier is empty, if you want to join to exisiting game, provide valid session id")

	url = f"{server}/join_to_game?player_name={bot_name}&session_id={session_id}"
 
	socket = await connect(url)
 
	__ENV_VARS["server"] = server
	__ENV_VARS["session_id"] = session_id
	__ENV_VARS["bot_name"] = bot_name
 
	return socket

def __run_bot(random_bot_class: Type[Agent], server: str, session_id: str, int_id: int, **agent_kwds):
	"""Helper function for bot execution

	Args:
		random_bot_class (Type[Agent]): Agent initializer
		server (str): server URL
		session_id (str): session identifier
		int_id (int): identifier of bot object
	"""
	
	url = f"{server}/join_to_game?player_name={random_bot_class.__name__}_{int_id}&session_id={session_id}"
 
	def wrapper():
		"""Wrapper for networking tasks execution during bot interaction with game.
		"""
		_ = __connection_proxy(connect)(url)
		bot = random_bot_class(**agent_kwds)
  
		def bot_loop():
			"""Bot behaviour
			"""
			bot.handle_new_states(None)
			done = False
			while not done:
				_ = bot.choose_action()
				done = bot.is_done
				sleep(0.1)
			else: logger.info(f"BOT: {type(bot)} is dead")
		bot_loop()
	wrapper()
	
def spawn_random_bots(server: str, session_id: str, random_bot_class: Type[Agent], count: int, **agent_kwds):
	"""Spawns some random bots on server 

	Args:
		server (str): URL of target server
		session_id (str): session identifier of game
		random_bot_class (Type): initializer of bot objects
		count (int): count of bots to spawn
		agent_kwds: agent's constructor parameters
	"""
	
	executor = cf.ProcessPoolExecutor(max_workers=count)
	_futures = {num: executor.submit(__run_bot, random_bot_class, server, session_id, num, **agent_kwds) for num in range(count)}
	for num, future in (_futures.items()): future.add_done_callback(lambda _: logger.info(f"Process of bot No. {num} is finished"))
	
	return (executor, _futures)
	
__all__ = [Agent, Action, get_session_id, spawn_random_bots, make_env]