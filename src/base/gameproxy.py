from typing import Any, Callable, Coroutine, Dict
from websockets.legacy.client import WebSocketClientProtocol
from websockets.typing import Data
from .action import Action
import orjson
import gzip
import asyncio
from functools import partial


class __GameConnectionHandler:
	__socket: WebSocketClientProtocol =None


class __ConnectionProxy:
	
	"""Defines a proxy class to handle implicit communication between
	  (it does not matter whether it is local or public) game-server 
	  and implemented agent
	"""
		
	def __init__(self, socket_provider: Callable[..., Coroutine[Any, Any, WebSocketClientProtocol]]) -> None:
		"""Creates an instance of __GameProxy class as a wrapper of provided async function that handles connection with game_server

		Args:
			socket_provider (*args, **kwargs) -> Coroutine[Any, Any, WebSocketClientProtocol]: Function that connects with server endpoint and yields socket
		"""
		
		self.__socket_provider = socket_provider

	async def __call__(self, *args: Any, **kwds: Any) -> WebSocketClientProtocol:
		"""Calls wrapped socket_provider function

		Returns:
			WebSocketClientProtocol: Obtained socket
		"""
		socket: WebSocketClientProtocol = await self.__socket_provider(*args, **kwds)
		await asyncio.sleep(0)
		__GameConnectionHandler.__socket = socket
		return socket

	def __get__(self, instance, cls=None):
		partial(self.__call__, instance)	


class __SendProxy:
	def __init__(self, action_getter: Callable[..., Action]) -> None:
		self.__action_getter = action_getter
	
	def __call__(self, *args: Any, **kwds: Any) -> Any:
		action: Action = self.__action_getter(*args, **kwds)
		loop = asyncio.get_event_loop()
		async def __send():
			await __GameConnectionHandler.__socket.send(gzip.compress(orjson.dumps(action.encode())))
			await asyncio.sleep(0)
		loop.run_until_complete(__send)
		return action

	def __get__(self, instance, cls=None):
		partial(self.__call__, instance)
	
 
class __ReceiveProxy:
	def __init__(self, new_message_handler: Callable[..., Coroutine[Any, Any, None]]) -> None:
		self.__handler = new_message_handler
	
	async def __call__(self, *args: Any, **kwds: Any) -> Any:
		while True:
			message: Data =await __GameConnectionHandler.__socket.recv()
			await asyncio.sleep(0)
			await self.__handler(orjson.loads(gzip.decompress(message)))

	def __get__(self, instance, cls=None):
		partial(self.__call__, instance)
  
connection_proxy = __ConnectionProxy
send_proxy = __SendProxy
receive_proxy = __ReceiveProxy