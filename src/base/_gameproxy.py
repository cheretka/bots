from abc import ABCMeta, abstractclassmethod, abstractmethod
from asyncio.tasks import sleep
from concurrent.futures.thread import ThreadPoolExecutor
import concurrent.futures as cf
import logging
import threading
from typing import Any, Callable, Coroutine, List
from websockets.legacy.client import WebSocketClientProtocol
from websockets.typing import Data
from .action import Action
import orjson
import gzip
import asyncio
from functools import partial
from threading import Thread
import traceback


class _ThreadedAsyncioExecutor(Thread):
	"""	Defines an executor to take control over submitting tasks to the 
	
	"""
	
	def __init__(self):
		super().__init__()
		self._loop = asyncio.new_event_loop()
		asyncio.set_event_loop(self._loop)
		self.daemon = True
		self.proxies: List[_Proxy] = []
		self.__coros: List[Coroutine[Any, Any, Any]] = []
		
	def submit(self, coro: Coroutine[Any, Any, Any]):
		self.__coros.append(coro)
		fut = asyncio.run_coroutine_threadsafe(self.schedule_subscription_task(coro), self._loop)
		fut.add_done_callback(lambda _: self.__coros.remove(coro))
		return fut
	
	async def schedule_subscription_task(self, coro: Coroutine[Any, Any, Any]):
		result = await coro
		await asyncio.sleep(0)
		return result
	
	def run(self):
		self._loop.run_forever()

	def stop(self):
		print("Cleaning thread...")
		for proxy in self.proxies:
			proxy.teardown()

		for coro in self.__coros:
			try:
				coro.close()
			except:
				pass
		
		self._loop.close()		
		
			
class __GameConnectionHandler:
	
	__socket: WebSocketClientProtocol =None
	__coro_thread: _ThreadedAsyncioExecutor = _ThreadedAsyncioExecutor()
	__host: str= ""
 
	@property
	def coro_executor(self): 
		if not self.__coro_thread.is_alive(): 
			self.__coro_thread.start()
		return self.__coro_thread
	
	@property
	def socket(self): return self.__socket
 
	@socket.setter
	def socket(self, _socket: WebSocketClientProtocol): 
		self.__socket = _socket
		self.__host = _socket.host
	
	def close(self):
		print("In close")
		async def __clean_up_connection():
			await self.__socket.close_connection()
			await asyncio.sleep(0)
			await self.__socket.close()
			await asyncio.sleep(0)
   
		if self.__socket is not None:
			future = self.coro_executor.submit(__clean_up_connection())
			future.add_done_callback(lambda _: print("Finished an attempt to disconnect from host\n"))
			for completed_future in cf.as_completed([future]): 
				print("Collecting...")
				completed_future.result()
				print(f"Succesfully disconnected from host: {self.__host}")
	
		self.coro_executor.stop()

class _Proxy(metaclass=ABCMeta):
	def __init__(self) -> None:
		self._event = threading.Event()
		self._task: Coroutine[Any, Any, Any] =None
	
	def teardown(self):
		print(f"Terminating: {self}")
		self._event.set()
		if self._task is not None:
			self._task.close()
	
	@abstractmethod
	def _call(self, *args: Any, **kwargs: Any):...
 
	def __call__(self, *args: Any, **kwds: Any):
		return self._call(*args, **kwds)

	def __get__(self, instance, cls=None):
		"""	Binds wrapped function with instance - the owner of method.

		Args:
			instance (object): instance of Agent to bind with captured function
			cls Optional[Type]: subclass of Agent. Defaults to None.
		"""
		return partial(self.__call__, instance)	


class __ConnectionProxy(_Proxy):
	
	"""	Defines a proxy class to handle implicit connection between
		(it does not matter whether it is local or public) game-server 
		and implemented agent
	"""
		
	def __init__(self, socket_provider: Callable[..., Coroutine[Any, Any, WebSocketClientProtocol]]) -> None:
		"""	Creates an instance of __GameProxy class as a wrapper of provided async function that handles connection with game_server

		Args:
			socket_provider (*args, **kwargs) -> Coroutine[Any, Any, WebSocketClientProtocol]: Function that connects with server endpoint and yields socket
		"""
		super().__init__()
		self.__socket_provider = socket_provider

	def _call(self, *args: Any, **kwds: Any) -> WebSocketClientProtocol:
		"""	Calls wrapped socket_provider function

		Returns:
			WebSocketClientProtocol: Obtained socket
		"""
		self._task = self.__socket_provider(*args, **kwds)
  
		future = _h_conn.coro_executor.submit(self._task)
		future.add_done_callback(lambda _: print("Finished an attempt to connect with host\n"))
  
		for f in cf.as_completed([future]):
			socket: WebSocketClientProtocol =f.result()
   
		self._task = None
		_h_conn.socket = socket
		return socket


class __SendProxy(_Proxy):
	"""	Defines a proxy class to handle implicit transfer of chosen action from agent to game-server, that is, it takes the 
		responsibilty of notifying a server about taken action from client.
	   
	"""
	def __init__(self, action_getter: Callable[..., Action]) -> None:
		""" Creates an instance of __SendProxy class as a wrapper of provided function that returns an action to take by agent.

		Args:
			action_getter (*args, **kwargs) -> Action: Function that returns an action
		"""
		super().__init__()
		self.__action_getter = action_getter
	
	def _call(self, *args: Any, **kwds: Any) -> Action:
		""" Send to server a chosen action. 

		Returns:
			Action: Chosen action
		"""
		action: Action = self.__action_getter(*args, **kwds)
	
		async def __send():
			self._task = _h_conn.socket.send(gzip.compress(orjson.dumps(action.encode())))
			await self._task
			await asyncio.sleep(0)
			return action

		future = _h_conn.coro_executor.submit(__send())
  
		for f in cf.as_completed([future]):
			action = f.result()
   
		self._task = None
		return action
	
 
class __ReceiveProxy(_Proxy):
	""" Defines a proxy class to handle implicit transfer of game-state from game-server to agent, that is, it takes the 
		responsibilty of collecting new states from agent.
	
	"""
	
	def __init__(self, new_message_handler: Callable[..., None]) -> None:
		"""	Creates an instance of __ReceiveProxy class as a wrapper provided function that is nothing but a handler of 
			incoming new game-state

		Args:
			new_message_handler (*args, **kwargs) -> None: Function that handles new state.
		"""
		super().__init__()
		self.__handler = new_message_handler
	
	def _call(self, *args: Any, **kwds: Any) -> None:   
		"""	Runs an infinite loop to handle new states. 
		"""
		async def __receive():
			while True and not self._event.is_set():
				self._task = _h_conn.socket.recv()
				message: Data = await self._task
				decompressed = orjson.loads(gzip.decompress(message))
				logging.debug(f"Obtained data from server; raw={message}; decompressed={decompressed}")
				
				self.__handler(args[0], decompressed)
				await asyncio.sleep(0)
	
			if not self._task.cr_running: self._task = None
   
		_h_conn.coro_executor.submit(__receive()).add_done_callback(lambda x: print(f"Exception: {x.exception()}", traceback.print_tb(x.exception().__traceback__)))
  
def cleanup():
	logging.info("In cleanup")
	_h_conn.close()

connection_proxy = __ConnectionProxy
send_proxy = __SendProxy
receive_proxy = __ReceiveProxy
_h_conn = __GameConnectionHandler()
__all__ = [connection_proxy, send_proxy, receive_proxy, cleanup]