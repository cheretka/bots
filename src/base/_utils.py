from threading import Thread, RLock as Lock
from multiprocessing import Pipe
from typing import Any, Callable, Coroutine, Dict, List, Type, Tuple
from asyncio.events import AbstractEventLoop
from asyncio.tasks import Task
import concurrent.futures as cf
import asyncio
import traceback
from functools import partial
from multiprocessing.pool import AsyncResult, Pool as P

from .. import _logger


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
				_logger.warn("Unregistered exception occurred: ", type(exception), " -> " , exception)
				traceback.print_exception(type(exception), exception, exception.__traceback__)
		else:
			msg = context.get("message", None)
			if msg: _logger.warn(msg)

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
			_logger.warn("Closing a loop")
			self._loop.close()		
   
	def cancel_tasks(self):
		"""Cancels stored tasks.
		"""
		[task.cancel() for task in self.__tasks]
 
	def stop(self):
		"""Stops ThreadedAsyncioExecutor object. Cancels all coroutines that are queued in event-loop system and then stops an event-loop. 
		"""
	
		if self.stopped: return
		_logger.info("Cleaning thread...")
		   
		async def _shutdown():
			tasks = []

			for coro in asyncio.all_tasks(self._loop):
    
				_logger.info(f"The state of a coroutine at {hex(id(coro))}:", coro._state)	
				if coro is not asyncio.current_task(self._loop):
    
					if not coro.done():
						coro.cancel()
						tasks.append(coro)
			if tasks:
				_logger.info(f"Closing {len(tasks)} tasks")
				await asyncio.gather(*tasks, loop=self._loop, return_exceptions=True)
    
		_, fut = self.submit(_shutdown())
		fut.add_done_callback(lambda _: self._set_stopped())
		cf.wait([fut])
		fut.result()
  
		self._loop.stop()		
  
  
class _Bots_Manager:
	"""Definition of _Bots_Manager to take care of spawned agents.
	"""
	
	def __init__(self, params: List[Tuple[P, List[AsyncResult], List[Event]]]) -> None:
		self.__params = params
  
	def terminate(self, timeout=10):
		"""Terminates BotsManager object after given timeout. Sets events to stop managed processes, and collects multiprocessing.AsyncResult objects.

		Args:
			timeout (int, optional): time to wait. Defaults to 10.
		"""
		for __executor, __futures, __events in self.__params:
			
			for event in __events:
				event.set()

			for future in __futures:
				try:
					
					_logger.info("Wait for the AsyncResult at: ", hex(id(future)))
					future.get(timeout=timeout)
				except Exception as _time:
					_logger.warn(f"Unable to kill bot process safely -> {type(_time)}")
	
			_logger.info(f"Pool at: {hex(id(__executor))}, is about to shutdown...")
			__executor.terminate()
			__executor.close()