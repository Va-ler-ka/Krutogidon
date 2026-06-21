from __future__ import annotations

import json

from src.game.engine import GameEngine
from src.game.enums import ActionType, GamePhase
from src.game.models import Action, GameConfig
from src.game.serialization import state_to_json
from src.game.setup import setup_game


def test_state_serializes_phase() -> None:
    state, _database = setup_game(GameConfig(player_count=2, seed=22))

    payload = json.loads(state_to_json(state))

    assert payload["phase"] == GamePhase.MAIN


def test_end_turn_returns_to_main_for_next_player() -> None:
    state, database = setup_game(GameConfig(player_count=2, seed=23))
    engine = GameEngine(state, database)

    engine.step(Action(ActionType.END_TURN))

    assert state.phase == GamePhase.MAIN
    assert state.current_player_index == 1
