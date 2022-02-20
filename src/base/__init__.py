from multiprocessing import Pool
import threading
import traceback
from typing import Optional, Type
import random
from websockets.legacy.client import connect, WebSocketClientProtocol
import asyncio
from time import sleep
from ._utils import Event as _Event, _Bots_Manager
from ._gameproxy import connection_proxy as __connection_proxy, cleanup
from .agent import Agent
from .action import Action
from .stateupdater import StateUpdater
from .. import _logger, _set_var, _get_var

def get_session_id(): 
	return _get_var('session_id')

def make_env(server: str, name: str, game_type: str, 
				   bot_name: str, session_id: Optional[str] =None,
				   join: bool =False, spectator=False) -> WebSocketClientProtocol:
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
	

	socket: WebSocketClientProtocol = __make_env(server, name, game_type, bot_name, session_id, join, spectator)
	
	_logger.warn(f"Established connection at: {socket.host}")
	return socket
  
@__connection_proxy
async def __make_env(server: str, name: str, game_type: str, 
				   bot_name: str, session_id: Optional[str] =None,
				   join: bool =False, spectator=False) -> WebSocketClientProtocol:
	_set_var("name", name)
	_set_var('game_type', game_type)
	if not join:
		url = f"{server}/create_game?name={name}&type={game_type}"
		async with connect(url) as web_socket:
			session_id = await web_socket.recv()
			await asyncio.sleep(0)

	return await __join(server, session_id, bot_name, spectator)

async def __join(server: str, session_id: str, bot_name: str, spectator=False):
	"""Joins as bot to a session of given server.

	Args:
		server (str): websocket address of server.
		session_id (str): id of session to join, usually obtained from the make_env function
		bot_name (str): the name of the bot

	Raises:
		ValueError: if session_id is None or empty

	Returns:
		WebSocketClientProtocl: wrapped websocket to communicate with server.
	"""
	if not session_id: 
		raise ValueError("Provided session identifier is empty, if you want to join to exisiting game, provide valid session id")

	url = f"{server}/join_to_game?player_name={bot_name}&session_id={session_id}&is_spectator={spectator}"
 
	socket = await connect(url)
	#game_type = await socket.recv()
	# await asyncio.sleep(0)
 
	_set_var("server", server)
	
	_set_var("session_id", session_id)
	_set_var("bot_name", bot_name)

	return socket

def __run_bot(bot_class: Type[Agent], server: str, session_id: str, int_id: int, evt: _Event, game_type:str, **agent_kwds):
	"""Helper function for bot execution

	Args:
		bot_class (Type[Agent]): Agent initializer
		server (str): server URL
		session_id (str): session identifier
		int_id (int): identifier of bot object
	"""
	
	bot_name = f"{bot_class.__name__}_{int_id}"
	
	def wrapper():
		"""Wrapper for networking tasks execution during bot interaction with game.
		"""
		from sys import platform
		import signal
		if platform == "win32":
			import win32api, win32process, win32con

			pid = win32api.GetCurrentProcessId()
			handle = win32api.OpenProcess(win32con.PROCESS_ALL_ACCESS, True, pid)
			win32process.SetPriorityClass(handle, win32process.THREAD_PRIORITY_LOWEST)
		else:
			from os import nice
			nice(20)
		_set_var('game_type', game_type)	
		async def connect_to_url(bot_name): return await __join(server, session_id, bot_name)

		_ = __connection_proxy(connect_to_url)(bot_name)
  
		bot = bot_class(**agent_kwds)
  

		def poll_and_clean(*args, **kwargs):
			"""Polls a state of stored event and closes bot process if a state is set.
			"""
			while not evt.is_set():sleep(0.1)
			
			else: 
				_logger.info(f"Cleaning up bot. No {int_id}")
				terminate_bot()	
			
		def terminate_bot(*args, **kwargs):
			global done
			done = False
			evt.set()
			cleanup()
		signal.signal(signal.SIGINT, terminate_bot)
		conn_cleaner = threading.Thread(daemon=True, target=poll_and_clean)
		conn_cleaner.start()
		bot.handle_new_states(None)
		done = False
   
		try:
			while not done and not evt.is_set():
				sleep(random.random())
				
				_ = bot.choose_action()
				_logger.info(f"Chosen action {_} goes brr")
				done = bot.is_done
			else: print(f"BOT: {type(bot)} is dead")
   
		except Exception as e:
			_logger.warn(f"BOT: {type(bot)} is dead, exception occurred {e}.")
			traceback.print_tb(e.__traceback__)
   
		return int_id

	return wrapper()
	
def spawn_bots(server: str, session_id: str, bot_class: Type[Agent], count: int, **agent_kwds):
	"""Spawns some random bots on server 

	Args:
		server (str): URL of target server
		session_id (str): session identifier of game
		bot_class (Type): initializer of bot objects
		count (int): count of bots to spawn; max of count is 100
		agent_kwds: agent's constructor parameters
	"""
	if _get_var('game_type') == "":
		import requests as rq
		import urllib3.util.url as u
		url: u.Url = u.parse_url(server)
		http_port = _get_var('http_port')
		url = u.Url(scheme='http',
                	host=url.host,
                  	port=int(http_port)).url
		
		response = rq.get(f"{url}/games/{session_id}").json()
		_set_var('game_type', response.get('game_type', ''))
 
	from sys import platform
	_MAX_COUNT_OF_WIN32_WAIT_FOR_MULTIPLE_OBJECTS = 63 - 2 #2 workers needed as a overhead for ProcessPoolExecutor and multiprocessing.Pool as well
	_TOTAL_MAX = 100
	count = min(count, _TOTAL_MAX)
 
	def __make(count_of_workers: int, curr:int =0):
		executor = Pool(processes=count_of_workers)
		
		_events = [_Event() for _ in range(count_of_workers)]
		_futures = {num: executor.apply_async(__run_bot, (bot_class, server, session_id, num, _events[num-curr], _get_var('game_type')), 
										 	  agent_kwds, callback=lambda _: _logger.info(f"Process of bot No. {_} is finished")
										) for num in range(curr, curr + count_of_workers)}
		
		return executor, list( _futures.values()), _events

	if platform == "win32":
		params = []
		workers = count - _MAX_COUNT_OF_WIN32_WAIT_FOR_MULTIPLE_OBJECTS
		_curr = 0
		while workers > 0:
			params.append(__make(_MAX_COUNT_OF_WIN32_WAIT_FOR_MULTIPLE_OBJECTS, _curr))
			workers -= _MAX_COUNT_OF_WIN32_WAIT_FOR_MULTIPLE_OBJECTS
			_curr += _MAX_COUNT_OF_WIN32_WAIT_FOR_MULTIPLE_OBJECTS
		else:
			params.append(__make(workers + _MAX_COUNT_OF_WIN32_WAIT_FOR_MULTIPLE_OBJECTS, _curr))
			
	else:
		executor, _futures, _events = __make(count)
		params = [(executor, _futures, _events)]
	
	return _Bots_Manager(params)
	
__all__ = [Agent, Action, get_session_id, spawn_bots, make_env, cleanup]