from __future__ import annotations
from ..base.action import Action
from enum import Enum
from typing import List, Dict


class AgarntAction(Action, Enum):
	"""Defines an action structure for Agarnt game
	"""
	
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
		"""Returns  a list of actions available in agarnt game

		Returns:
			List[AgarntAction]: list of actions
		"""
		if cls._all is None:
			cls._all = list(map(lambda item:item[1], filter(lambda item: not "KEYS" in item[0], cls.__members__.items())))
		return cls._all

	def encode(self) -> Dict[str, Dict[str, bool]]:
		"""Encodes single action into proper dictionary, that is understandable for the server-side

		Returns:
			Dict[str, Dict[str, bool]]: Dictionary that contains boolean flags for each available basic action (Left, Down, Right, Up) -> if action is complex, more than one basic action is active.
		"""
		name = self.name
		d = {k:False for k in AgarntAction.__KEYS.value}
		for char in name: d[char] = True
		return {"directions" : d}
	
	@classmethod
	def decode(cls, d: Dict[str, Dict[str, bool]]):
		"""Decodes obtained dictionary into AgarntAction variable

		Args:
			d (Dict[str, Dict[str, bool]]): Obtained, decompressed and de-jsonized data obtained from server

		Returns:
			AgarntAction: Decoded action
		"""
		d = d["directions"]
		name = "".join(map(lambda item: item[0],sorted(filter(lambda item:item[1], d.items()), key=lambda x: 0 if x[0] in ["L", "R"] else 1 )))
		return AgarntAction[name]
