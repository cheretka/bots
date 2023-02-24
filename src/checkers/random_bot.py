import numpy as np

from .action import CheckersAction
from .checkers_board import CheckersBoard
from ..base import Agent


class RandomBot(Agent):


    def __init__(self, generator: np.random.Generator):
        super().__init__(CheckersAction)
        self.__rng = generator

    def choose_action(self) -> CheckersAction:
        print("\nchoose_action")
        if self.current_state:
            if self.current_state.my_move:
                pos_moves = self.current_state.get_possible_moves()
                print("pos_moves", pos_moves)
                chosen_action = self.__rng.choice(pos_moves)
                print("chosen_action\n", chosen_action)
                return chosen_action  # like [[1, 2], [3, 4]]
            else:
                return None
        else:
            return None

    def handle_new_states(self, msg):
        print("\nhandle_new_states msg", msg)
        self.current_state = CheckersBoard(msg)

    @property
    def is_done(self) -> bool:
        if isinstance(self.current_state, CheckersBoard):
            return self.current_state.game_status in ["lost", "won", "draw"]
        return False


    def update(self):
        ...
