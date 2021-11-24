from __future__ import annotations
from typing import List
from abc import ABCMeta, abstractclassmethod, abstractmethod

class Action(metaclass=ABCMeta):
	_all = None
	
	@abstractmethod
	def encode(self):...
	
	@abstractclassmethod
	def get_all(cls)->List[Action]:...
	
	@abstractclassmethod
	def decode(cls, data)->Action:...