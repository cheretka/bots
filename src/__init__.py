from __future__ import annotations
import logging as _logging
import os

from typing import Any as _Any, Type as _Type, Dict as _Dict, Tuple as _Tup

_level = _logging.WARNING if 'PRODUCTION' in os.environ else _logging.DEBUG
_logger = _logging.getLogger(__name__) 
_logger.setLevel(_level)
_logger.info("Logging level is equal to: ", _logging.getLevelName(_level))

_ENV_VARS = {
	"name":"",
	"server":"",
	"session_id":"",
	"game_type":"",
	"bot_name":""
}

_UPDATERS: _Dict[str, _Tup[_Type[StateUpdater], _Tup[_Any], _Dict[str, _Any]]] = {
	"":...
}

def _get_var(key: str) -> str: 
	return _ENV_VARS.get(key, "")

def _set_var(key: str, value: str): 
	_ENV_VARS[key] = value

def register_updater_args(game_type: str, *args, **kwargs):
	t = _UPDATERS.get(game_type, None)
	_UPDATERS[game_type] = (t[0] if t else t, args, kwargs)
	
def register_updater(game_type: str, type: _Type[StateUpdater]):
	t = _UPDATERS.get(game_type, None)
	_UPDATERS[game_type] = (type, tuple(), {}) if not t else (type, t[1], t[2])

def _get_updater_initialization_params(key: str): return _UPDATERS.get(key, None)

from .base import Agent, Action, make_env, spawn_bots, get_session_id, cleanup, StateUpdater
from .agarnt import AgarntAction, RandomAgent, CloseFoodAgent, GradAgent, AgarntStateUpdater

__all__ = [
	Agent, Action, make_env, spawn_bots, get_session_id, cleanup, StateUpdater,
	AgarntAction, RandomAgent, CloseFoodAgent, GradAgent, AgarntStateUpdater, register_updater, register_updater_args
]

register_updater("agarnt", AgarntStateUpdater)
register_updater_args("agarnt", {})

