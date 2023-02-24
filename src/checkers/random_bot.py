import numpy as np
from .action import CheckersAction
from .checkers_board import CheckersBoard
from ..base import Agent


class RandomBot(Agent):

    def __init__(self, generator: np.random.Generator):
        super().__init__(CheckersAction)
        self.__rng = generator

    def choose_action(self) -> CheckersAction:
        print("\nfun choose_action()")
        if self.current_state and self.current_state.my_move:
            chosen_action = self.__rng.choice(self.current_state.get_possible_moves())
            print("move\n", chosen_action)
            act = CheckersAction(chosen_action.tolist())
            return act

        return CheckersAction([])

    def handle_new_states(self, msg):
        print("\nfun handle_new_states() msg", msg)
        self.current_state = CheckersBoard(msg)

    @property
    def is_done(self) -> bool:
        if isinstance(self.current_state, CheckersBoard):
            return self.current_state.game_status in ["lost", "won", "draw"]
        return False


    def update(self):
        ...
