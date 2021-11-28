from ..base import Agent
from .action import AgarntAction
import numpy as np

class RandomAgent(Agent):
	
	def __init__(self, generator: np.random.Generator):
		super().__init__(AgarntAction)
		self.__rng = generator
  
	def choose_action(self) -> AgarntAction:
		return self.__rng.choice(self.action_provider.get_all())

	def handle_new_states(self, msg):
		self.current_state = msg
	
	@property
	def is_done(self) -> bool:
		if "d" in self.current_state:
			return self.current_state["d"]
		return False

	def update(self):
		...