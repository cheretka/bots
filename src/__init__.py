import logging
import os

level = logging.WARNING if 'PRODUCTION' in os.environ else logging.DEBUG
print("Logging level is equal to: ", logging.getLevelName(level))
logger = logging.getLogger(__name__) 
logger.setLevel(level)

from .base import Agent, Action, make_env, spawn_bots, get_session_id, cleanup, StateUpdater
from .agarnt import AgarntAction, RandomAgent, CloseFoodAgent, AgarntStateUpdater