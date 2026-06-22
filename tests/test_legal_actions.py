from __future__ import annotations

from src.game.engine import GameEngine
from src.game.enums import ActionType, GamePhase
from src.game.models import Action, GameConfig
from src.game.setup import setup_game


def test_legal_actions_include_play_and_end_turn() -> None:
    state, database = setup_game(GameConfig(player_count=2, seed=20))
    engine = GameEngine(state, database)

    actions = engine.legal_actions()

    assert any(action.type == ActionType.PLAY_CARD for action in actions)
    assert any(action.type == ActionType.END_TURN for action in actions)
    assert all(action.actor_id == state.current_player.id for action in actions)


def test_illegal_action_is_rejected() -> None:
    state, database = setup_game(GameConfig(player_count=2, seed=21))
    engine = GameEngine(state, database)

    try:
        engine.step(Action(ActionType.BUY_MARKET_CARD, market_index=99))
    except ValueError as error:
        assert "Illegal action" in str(error)
    else:
        raise AssertionError("Expected illegal action to be rejected")


def test_attack_without_target_creates_pending_choice_in_three_player_game() -> None:
    state, database = setup_game(GameConfig(player_count=3, seed=34))
    engine = GameEngine(state, database)
    wand_id = database.starter_cards["Палочка"]
    state.current_player.hand = [wand_id]

    play_action = next(action for action in engine.legal_actions() if action.type == ActionType.PLAY_CARD)
    assert play_action.target_player is None

    engine.step(play_action)

    assert state.phase == GamePhase.CHOOSE_TARGET
    assert state.pending_choice is not None
    assert len(engine.legal_actions()) == 3
