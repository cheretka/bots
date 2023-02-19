from ..base import Agent
from .action import CheckersAction
import numpy as np


class RandomBot(Agent):

    def __init__(self, generator: np.random.Generator):
        super().__init__(CheckersAction)
        self.__rng = generator

    def choose_action(self) -> CheckersAction:
        random_action = self.__rng.choice(self.action_provider.get_all())
        self.action_provider.board_state.chosen_move = random_action
        return random_action

    def handle_new_states(self, msg):
        self.current_state = msg

    @property
    def is_done(self) -> bool:
        if "game_status" in self.current_state:
            return self.current_state["game_status"] in ["lost", "won", "draw"]
        return False

    def update(self):
        ...
