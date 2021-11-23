from __future__ import annotations
from typing import List

class Action:
	_all = None
	
	def encode(self):...
	
	@classmethod
	def get_all(cls)->List[Action]:...
	
	@classmethod
	def decode(cls, data)->Action:...