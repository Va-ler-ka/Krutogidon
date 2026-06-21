from __future__ import annotations

import json

from src.game.models import GameConfig
from src.game.serialization import state_to_json
from src.game.setup import setup_game


def test_state_serializes_to_json() -> None:
    state, _database = setup_game(GameConfig(player_count=2, seed=12))

    payload = json.loads(state_to_json(state))

    assert payload["turn_number"] == 1
    assert len(payload["players"]) == 2
