from __future__ import annotations
from ..base.action import Action
from enum import Enum
from typing import List, Dict


class AgarntAction(Action, Enum):
	
	L = 0
	D = 1
	R = 2
	U = 3
	LD = 4
	LU = 5
	RD = 6
	RU = 7
	
	__KEYS = ["L", "D", "R", "U"]
	
	@classmethod
	def get_all(cls)->List[AgarntAction]:
		if cls._all is None:
			cls._all = list(map(lambda item:item[1], filter(lambda item: not "KEYS" in item[0], cls.__members__.items())))
		return cls._all

	def encode(self) -> Dict[str, bool]:
		name = self.name
		d = {k:False for k in AgarntAction.__KEYS.value}
		for char in name: d[char] = True
		return d
	
	@classmethod
	def decode(cls, d: Dict[str, bool]):
		name = "".join(map(lambda item: item[0],filter(lambda item:item[1], d.items())))
		return AgarntAction[name]
