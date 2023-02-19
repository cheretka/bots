from typing import Any, Dict
from ..base import StateUpdater


class CheckersStateUpdater(StateUpdater):
    _current_state: Dict[str, Any]

    def _update(self, update_to_apply: Dict[str, Any]) -> Dict[str, Any]:
        self._current_state.update(**update_to_apply)
        return self._current_state
