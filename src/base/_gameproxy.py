from __future__ import annotations
from abc import ABCMeta, abstractmethod
from asyncio.events import AbstractEventLoop
from asyncio.tasks import Task
import concurrent.futures as cf
from typing import Any, Callable, Coroutine, Dict, List, Type
from asyncio.exceptions import CancelledError
from websockets.legacy.client import WebSocketClientProtocol
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK
from websockets.typing import Data
from .action import Action
import orjson
import gzip
import asyncio
from functools import partial
from threading import Thread, RLock as Lock
from multiprocessing import Pipe
import traceback
from .. import logger


class Event(object):
	"""Implementation of Event class, that is based on "pipes" system
	"""
	def __init__(self):
		self._read_fd, self._write_fd = Pipe()
	
	def wait(self, timeout=None):
		"""Waits for a given timeout and get information about the state of the Event
		
		Keyword arguments:
		timeout -- time in seconds to wait
		Returns: True, if the Event object is set after provided timeout, False otherwise
  
		"""
		
		return self._read_fd.poll(timeout)
	
	def set(self):
		"""Sets the state of the Event object.
		"""
		if not self.is_set():
			self._write_fd.send(b"1")

	def clear(self):
		"""Unsets the state of the Event object.
		"""
		if self.is_set():
			self._read_fd.recv()

	def is_set(self):
		"""Checks if the Event object is in set state.
		Returns: see wait method
		"""
		return self.wait(0)

	def __del__(self):
		"""Closes the "pipes" system of the Event
		"""
		self._read_fd.close()
		self._write_fd.close()
 
	def fileno(self): 
		"""Returns the file descriptor of obtained "pipes" system.

		Returns:
			int: a file descriptor of the one of the end of pipe.
		"""
		return self._read_fd.fileno()
 

class _ThreadedAsyncioExecutor(Thread):
	"""	Defines an executor to take a control over submitted tasks to the asyncio.
	
	"""
	
	def __init__(self):
		super().__init__()
		self._loop = asyncio.new_event_loop()
		asyncio.set_event_loop(self._loop)
		self.daemon = True
		self._lock = Lock()
		self._stopped = Event()
		self._started = Event()
		self.__tasks: List[Task] = []
		self.__exception_handlers: Dict[Exception, List[Callable[..., Any]]] = {}
		self._loop.set_exception_handler(lambda loop, context:partial(self.__handle_errors)(loop, context))
	
	@property
	def stopped(self): 
		"""Returns information whether or not the thread is stopped.

		Returns:
			bool: the "stopped" state of thread.
		"""
		
		with self._lock: return self._stopped.is_set()
	
	@property
	def started(self) -> bool: 
		"""Returns information whether or not the thread is started.

		Returns:
			bool: the "started" state of thread.
		"""
		with self._lock: return self._started.is_set()
 
	def _set_stopped(self): 
		"""Sets the "stopped" Event of ThreadedAsyncioExecutor.
		"""
		with self._lock: self._stopped.set()
 	
	def __handle_errors(self, loop: AbstractEventLoop, context: Dict[str, Any]):
		"""Error handler that is run by asyncio every time the exception in a coroutine occurs.

		Args:
			loop (AbstractEventLoop): active event-loop
			context (Dict[str, Any]): asyncio exception context
		"""
		
		exception: Exception =context.get("exception", None)
  
		if exception:
			handler_list = self.__exception_handlers.get(type(exception), None)
   
			if handler_list: [handler(exception) for handler in handler_list]
			else: 
				logger.warn("Unregistered exception occurred: ", type(exception), " -> " , exception)
				traceback.print_exception(type(exception), exception, exception.__traceback__)
		else:
			msg = context.get("message", None)
			if msg: logger.warn(msg)

		if loop.is_running():
			self.stop()
 
	def register_exception(self, exception: Type[Exception], handler: Callable[..., Any]):
		"""Registers a handler for a given exception type

		Args:
			exception (Type[Exception]): type of exception to store in handlers' dictionary.
			handler (Callable[..., Any]): callable to call after that a given type of exception occurred.
		"""
		if exception in self.__exception_handlers:
			self.__exception_handlers[exception].append(handler)
		else:
			self.__exception_handlers[exception] = [handler]
  
	def submit(self, coro: Coroutine[Any, Any, Any]):
		"""Submits coroutine into wrapped asyncio event loop.

		Args:
			coro (Coroutine[Any, Any, Any]): coroutine to run.

		Returns:
			Tuple[Task, Future]: returns Task and Task wrapped by concurrent.futures.Future
		"""
		task = self._loop.create_task(coro)
		self.__tasks.append(task)
		fut = asyncio.run_coroutine_threadsafe(self.__schedule_subscription_task(task), self._loop)
		fut.add_done_callback(lambda _: self.__tasks.remove(task))
		return task, fut
	
	async def __schedule_subscription_task(self, task: Task):
		"""Schedules given task to await.

		Args:
			task (Task): task to await

		Returns:
			Any: value collected from Task object.
		"""
		result = await task
		await asyncio.sleep(0)
		return result
	
	def run(self):
		"""Runs ThreadedAsyncioExecutor.
		"""
		try:
			self._loop.run_forever()
		except Exception as e: print(e.__traceback__)
		finally:
			logger.warn("Closing a loop")
			self._loop.close()		
   
	def cancel_tasks(self):
		"""Cancels stored tasks.
		"""
		[task.cancel() for task in self.__tasks]
 
	def stop(self):
		"""Stops ThreadedAsyncioExecutor object. Cancels all coroutines that are queued in event-loop system and then stops an event-loop. 
		"""
	
		if self.stopped: return
		logger.info("Cleaning thread...")
		   
		async def _shutdown():
			tasks = []

			for coro in asyncio.all_tasks(self._loop):
    
				logger.info(f"The state of a coroutine at {hex(id(coro))}:", coro._state)	
				if coro is not asyncio.current_task(self._loop):
    
					if not coro.done():
						coro.cancel()
						tasks.append(coro)
			if tasks:
				logger.info(f"Closing {len(tasks)} tasks")
				await asyncio.gather(*tasks, loop=self._loop, return_exceptions=True)
		_, fut = self.submit(_shutdown())
		fut.add_done_callback(lambda _: self._set_stopped())
		cf.wait([fut])

		fut.result()
		self._loop.stop()				


class __GameConnectionHandler:
	"""Definition of a handler of a connection with a game-server.
	"""
	__socket: WebSocketClientProtocol =None
	__coro_thread: _ThreadedAsyncioExecutor = _ThreadedAsyncioExecutor()
	__host: str= ""
	__proxies: List[_Proxy] = []
	
	@property 
	def proxies(self): 
		"""Returns current list of active proxies.

		Returns:
			List[_Proxy]: list of active proxies.
		"""
		return self.__proxies
 
	@property
	def coro_executor(self): 
		"""Returns an instance of ThreadedAsyncioExecutor. It also lazily starts the executor.

		Returns:
			_ThreadedAsyncioExecutor: an executor used by proxies to submit new coroutines.
		"""
		if not self.__coro_thread.started: 
			self.__coro_thread.start()
		return self.__coro_thread
	
	@property
	def socket(self): 
		"""Returns an instance of WebSocketClientProtocol

		Returns:
			WebSocketClientProtocol: stored instance of websocket.
		"""
		return self.__socket
 
	@socket.setter
	def socket(self, _socket: WebSocketClientProtocol): 
		"""Sets an instance of WebSocketClientProtocol 

		Args:
			_socket (WebSocketClientProtocol): instance of websocket.
		"""
		self.__socket = _socket
		self.__host = _socket.host
	
	def close(self):
		"""Closes all resources, cancels tasks, drops connections.
		"""
		logger.info("In close")
		for proxy in self.__proxies:
			proxy.teardown()

		self.coro_executor.cancel_tasks()

		async def __clean_up_connection():
			self.__socket.transfer_data_task.cancel()
			await self.__socket.close_connection()
			logger.info("Dropped connection")
			await asyncio.sleep(0)
			await self.__socket.close(1000)
			logger.info("Sent a socket disconnection code")
			await asyncio.sleep(0)
   
		if self.__socket is not None:
			
			logger.info("Cleaning connection...")
			_, future = self.coro_executor.submit(__clean_up_connection())
			future.add_done_callback(lambda _: logger.info("Finished an attempt to disconnect from host\n"))
			
			logger.info("Collecting futures...")
			try:
				logger.info("Collecting a future at:", hex(id(future)))
				done, _ = cf.wait([future])
				for completed_future in cf.as_completed(done): 
					
					completed_future.result()
					logger.warn(f"Succesfully disconnected from host: {self.__host}")
			except:
				future.set_exception(Exception("Forcibly closed coroutine"))
				future.cancel()
	
		self.coro_executor.stop()
  

class _Proxy(metaclass=ABCMeta):
	"""Base class of proxies.
	"""
	
	def __init__(self) -> None:
		self._event = Event()
		self._task: Task =None
		_h_conn.proxies.append(self)

	def teardown(self):
		"""Terminates Proxy object. Sets possessed Event object and cancels, if possible, current task.
		"""
		logger.info(f"Terminating: {self}")
		self._event.set()
		if self._task and not self._task.cancelled():
			self._task.cancel()
	
	@abstractmethod
	def _call(self, *args: Any, **kwargs: Any):...
 
	def __call__(self, *args: Any, **kwds: Any):
		"""Calls implementation of _call method provided by subclasses.

		Returns:
			Any: result of _call method delivered by subclass.
		"""
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
		coro = self.__socket_provider(*args, **kwds)
  
		self._task, future = _h_conn.coro_executor.submit(coro)
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
		_h_conn.coro_executor.register_exception(ConnectionClosedError, 
			lambda e:logger.warn(f"Connection dropped unsuccessfully, sending an action has been stopped with reason: {e.reason} and error code: {e.code}"))
		_h_conn.coro_executor.register_exception(ConnectionClosedOK, 
			lambda e:logger.warn("Connection dropped successfully, sending an action has been stopped"))
		self.__action_getter = action_getter
	
	def _call(self, *args: Any, **kwds: Any) -> Action:
		""" Sends to server a chosen action. 

		Returns:
			Action: Chosen action
		"""
		action: Action = self.__action_getter(*args, **kwds)
		if self._event.is_set(): return action
  
		async def __send():
			coro = _h_conn.socket.send(gzip.compress(orjson.dumps(action.encode())))
			try:
				await coro
			finally:
				await asyncio.sleep(0)
				return action

		self._task, future = _h_conn.coro_executor.submit(__send())
		try:
			for f in cf.as_completed([future]):
				action = f.result()
		except CancelledError: pass
		finally:
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
		_h_conn.coro_executor.register_exception(ConnectionClosedError, 
			lambda e:logger.warn(f"Connection dropped unsuccessfully, sending an action has been stopped with reason: {e.reason} and error code: {e.code}"))
		_h_conn.coro_executor.register_exception(ConnectionClosedOK, 
			lambda e:logger.warn("Connection dropped successfully, sending an action has been stopped"))
		self.__handler = new_message_handler
	
	def _call(self, *args: Any, **kwds: Any) -> None:   
		"""	Runs an infinite loop to handle new states. 
		"""
		async def __receive():
			try:
				while True and not self._event.is_set():
					coro = _h_conn.socket.recv()
					message: Data = await coro
					decompressed = orjson.loads(gzip.decompress(message))
					logger.info(f"Obtained data from server; raw={message}; decompressed={decompressed}")

					self.__handler(args[0], decompressed)
			except Exception as e:
				logger.info(f"Caught an exception: {e}. Ignored...")
			finally:
				await asyncio.sleep(0)
	   
		self._task, _ = _h_conn.coro_executor.submit(__receive())
  
def cleanup():
	"""Cleans up the handler of connection with websocket game-server.
	"""
	logger.info("Clean-up procedure of connection handler...")
	_h_conn.close()
	try:
		_h_conn.coro_executor.join(timeout=1)
	except Exception as e: 
		print(e)
		traceback.print_tb(e.__traceback__)

connection_proxy = __ConnectionProxy
send_proxy = __SendProxy
receive_proxy = __ReceiveProxy
_h_conn = __GameConnectionHandler()
__all__ = [connection_proxy, send_proxy, receive_proxy, cleanup, Event]