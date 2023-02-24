from __future__ import annotations
from typing import Dict
from ..base.action import Action


class CheckersAction(Action):

    def __init__(self, move) -> None:
        self.chosen_move = move

    def encode(self) -> Dict[str, array]:
        print("encode(), move=", self.chosen_move)
        if len(self.chosen_move) > 0:
            # return {"move": [[5, 6], [4, 5]]} # dzila, jest wysyłane na serwer
            return {"move": self.chosen_move}  # nie wysyła na serwer
        else:
            return {"not_move": 0}  # wysyła na serwer, ale chcialąbym zeby nie
