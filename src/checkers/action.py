from __future__ import annotations
from ..base.action import Action
from enum import Enum
from typing import List, Dict
from .checkers_board import CheckersBoard

class CheckersAction(Action, Enum):

    def __init__(self, *args) -> None:
        self.board_state = None

    @classmethod
    def get_all(cls) -> List[AgarntAction]:
        return self.board_state.get_possible_moves()

    def encode(self) -> Dict[str, Dict[str, bool]]:
        return {"move": self.board_state.chosen_move}

    @classmethod
    def decode(cls, state: Dict[str, Dict[str, bool]]):
        self.board_state = CheckersBoard(state)
        return self.board_state
