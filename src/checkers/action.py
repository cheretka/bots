from __future__ import annotations
from typing import Dict
from ..base.action import Action


class CheckersAction(Action):

    def __init__(self, move : list):
        self.chosen_move : list = move

    def encode(self) -> Dict[str, array]:
        print("encode(), move=\n", self.chosen_move)

        if len(self.chosen_move) > 0:
            tymcz = self.chosen_move.copy()
            self.chosen_move = {}
            return {"move": tymcz}

        return {}
