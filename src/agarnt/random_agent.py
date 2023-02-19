from ..base import Agent
from .action import AgarntAction
import numpy as np

class RandomAgent(Agent):

	def __init__(self, generator: np.random.Generator, eps =0.8):
		super().__init__(AgarntAction)
		self.__rng = generator
		self.__eps = eps
		self.__previous_action: AgarntAction =None

	def choose_action(self) -> AgarntAction:

		new_action = self.__rng.choice(self.action_provider.get_all())

		if self.__previous_action is not None:
			act = self.__rng.choice([self.__previous_action, new_action], p=[self.__eps, 1.0 - self.__eps])
			if act is not self.__previous_action: self.__previous_action = act
			return act

		else:
			self.__previous_action = new_action
			return self.__previous_action

	def handle_new_states(self, msg):
		self.current_state = msg

	@property
	def is_done(self) -> bool:
		if "d" in self.current_state:
			return self.current_state["d"]
		return False

	def update(self):
		...
