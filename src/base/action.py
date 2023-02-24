from __future__ import annotations
from typing import List


class Action():
	"""Abstract class for game action.
	"""
	_all = None

	def __init__(self, *args) -> None:
		pass

	def encode(self):...

	def get_all(cls)->List[Action]:...

	def decode(cls, data)->Action:...
