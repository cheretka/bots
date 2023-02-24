from __future__ import annotations

from typing import Dict

from .checkers_board import CheckersBoard
from ..base.action import Action


class CheckersAction(Action, CheckersBoard):

    def encode(self) -> Dict[str, array]:
        return {"move": [[0, 0], [1, 1]]}

    @classmethod
    def decode(cls, state: Dict[str, Dict[str, bool]]):
        print("I dont need this decode() function")
        return Null
