import abc
from typing import Any


class StateUpdater(metaclass=abc.ABCMeta):
	
	def __init__(self, init_state: Any) -> None:
		self._init_state = init_state
	
	@abc.abstractmethod
	def _update(self, update_to_apply: Any) -> Any:...
 
	def __call__(self, update_to_apply: Any) -> Any:
		return self._update(update_to_apply)