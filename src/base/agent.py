from enum import Enum
from .action import Action
from ._gameproxy import send_proxy as _send_proxy, receive_proxy as _receive_proxy
from abc import ABCMeta, abstractmethod, abstractproperty

class Agent(metaclass=ABCMeta):
	def __init__(self, action_provider: Action):
		self.action_provider = action_provider
		self.is_learning = False
		self.current_state = {}
		self.init_state = {}
		self.GAME_WIDTH = 0
		self.GAME_HEIGHT = 0
	
	def __init_subclass__(cls) -> None:
		cls.choose_action = _send_proxy(cls.choose_action)	
		cls.handle_new_states = _receive_proxy(cls.handle_new_states)
  
	@abstractmethod
	def choose_action(self) -> Action:...
	
	@abstractproperty
	def is_done(self) -> bool:...
 		
	@abstractmethod
	def handle_new_states(self, msg):...
	
	@abstractmethod
	def update(self):
		if not self.is_learning:
			return

__all__ = [Agent]