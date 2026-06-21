from __future__ import annotations

import json
from pathlib import Path

from .models import GameState


def state_to_json(state: GameState) -> str:
    return json.dumps(state.to_dict(), ensure_ascii=False, indent=2, default=str)


def save_state(state: GameState, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(state_to_json(state), encoding="utf-8")
