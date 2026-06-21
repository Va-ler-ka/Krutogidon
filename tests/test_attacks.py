from __future__ import annotations

from src.game.engine import GameEngine
from src.game.enums import ActionType
from src.game.models import Action, GameConfig
from src.game.setup import setup_game


def test_basic_attack_damage_is_applied_to_target() -> None:
    state, database = setup_game(GameConfig(player_count=2, seed=13))
    engine = GameEngine(state, database)
    player = state.current_player
    wand_id = database.starter_cards["Палочка"]
    player.hand = [wand_id]
    target = state.players[1]

    engine.step(Action(ActionType.PLAY_CARD, card_id=wand_id, target_player=target.id))

    assert target.health == 19
