from __future__ import annotations
from abc import ABCMeta, abstractmethod
from asyncio.tasks import Task
import concurrent.futures as cf
from typing import Any, Callable, Coroutine, List
from websockets.legacy.client import WebSocketClientProtocol
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK
from websockets.typing import Data
import orjson
import gzip
import asyncio
from functools import partial
import traceback

from .stateupdater import StateUpdater
from .action import Action
from ._utils import _ThreadedAsyncioExecutor, Event
from .. import _logger, _get_var, _get_updater_initialization_params


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
		_logger.info("In close")
		for proxy in self.__proxies:
			proxy.teardown()

		self.coro_executor.cancel_tasks()

		async def __clean_up_connection():
			self.__socket.transfer_data_task.cancel()
			await self.__socket.close_connection()
			_logger.info("Dropped connection")
			await asyncio.sleep(0)
			await self.__socket.close(1000)
			_logger.info("Sent a socket disconnection code")
			await asyncio.sleep(0)

		if self.__socket is not None:

			_logger.info("Cleaning connection...")
			_, future = self.coro_executor.submit(__clean_up_connection())
			future.add_done_callback(lambda _: _logger.info("Finished an attempt to disconnect from host\n"))

			_logger.info("Collecting futures...")
			try:
				_logger.info("Collecting a future at:", hex(id(future)))
				done, _ = cf.wait([future])
				for completed_future in cf.as_completed(done):

					completed_future.result()
					_logger.warn(f"Succesfully disconnected from host: {self.__host}")
			except:

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
		_logger.info(f"Terminating: {self}")
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
		future.add_done_callback(lambda _: _logger.info("Finished an attempt to connect with host"))

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
			lambda e:_logger.warn(f"Connection dropped unsuccessfully, sending an action has been stopped with reason: {e.reason} and error code: {e.code}"))
		_h_conn.coro_executor.register_exception(ConnectionClosedOK,
			lambda e:_logger.warn("Connection dropped successfully, sending an action has been stopped"))
		self.__action_getter = action_getter

	def _call(self, *args: Any, **kwds: Any) -> Action:
		""" Sends to server a chosen action.

		Returns:
			Action: Chosen action
		"""
		action: Action = self.__action_getter(*args, **kwds)
		if self._event.is_set(): return action

		async def __send():
			move_to_send = action.encode()
			if move_to_send:
				coro = _h_conn.socket.send(gzip.compress(orjson.dumps(move_to_send)))
				try:
					await coro
				finally:
					await asyncio.sleep(0)
					return action

		self._task, future = _h_conn.coro_executor.submit(__send())
		try:
			for f in cf.as_completed([future]):
				action = f.result()
		except Exception: pass
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
			lambda e:_logger.warn(f"Connection dropped unsuccessfully, sending an action has been stopped with reason: {e.reason} and error code: {e.code}"))
		_h_conn.coro_executor.register_exception(ConnectionClosedOK,
			lambda e:_logger.warn("Connection dropped successfully, sending an action has been stopped"))
		self.__handler = new_message_handler

	@property
	def __updater(self) -> StateUpdater:
		if not hasattr(self, "_state_updater"):
			game_type = _get_var("game_type")
			tup = _get_updater_initialization_params(game_type)
			if tup:
				updater_type, args, kwargs =  tup
				self._state_updater = updater_type(*args, **kwargs)
			else: return None
		return self._state_updater

	def _call(self, *args: Any, **kwds: Any) -> None:
		"""	Runs an infinite loop to handle new states.
		"""
		async def __receive():
			try:
				while True and not self._event.is_set():
					coro = _h_conn.socket.recv()
					message: Data = await coro
					decompressed = orjson.loads(gzip.decompress(message))
					_logger.info(f"Obtained data from server; raw={message}; decompressed={decompressed}")
					if self.__updater:
						decompressed = self._state_updater(decompressed)
					self.__handler(args[0], decompressed)
			except Exception as e:
				_logger.info(f"Caught an exception: {e}. Ignored...")
			finally:
				await asyncio.sleep(0)

		self._task, _ = _h_conn.coro_executor.submit(__receive())

def cleanup():
	"""Cleans up the handler of connection with websocket game-server.
	"""
	_logger.info("Clean-up procedure of connection handler...")
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
