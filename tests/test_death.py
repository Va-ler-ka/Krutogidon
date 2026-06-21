from __future__ import annotations

from src.game.engine import GameEngine
from src.game.enums import ActionType, GamePhase
from src.game.models import Action, GameConfig
from src.game.setup import setup_game


def test_player_receives_dead_wizard_token_on_death() -> None:
    state, database = setup_game(GameConfig(player_count=2, seed=32))
    engine = GameEngine(state, database)
    wand_id = database.starter_cards["Палочка"]
    attacker = state.players[0]
    target = state.players[1]
    attacker.hand = [wand_id]
    target.health = 1

    engine.step(Action(ActionType.PLAY_CARD, card_id=wand_id, target_player=target.id))

    assert len(target.dead_wizard_tokens) == 1
    assert target.health == state.config.death_reset_health


def test_empty_dead_wizard_stack_ends_game_on_death() -> None:
    state, database = setup_game(GameConfig(player_count=2, seed=33))
    engine = GameEngine(state, database)
    wand_id = database.starter_cards["Палочка"]
    state.dead_wizard_stack = []
    state.players[0].hand = [wand_id]
    state.players[1].health = 1

    engine.step(Action(ActionType.PLAY_CARD, card_id=wand_id, target_player=1))

    assert state.game_over is True
    assert state.phase == GamePhase.GAME_OVER
    assert state.end_reason == "dead_wizard_tokens_empty"
