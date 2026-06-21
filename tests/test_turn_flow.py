from __future__ import annotations

from src.game.engine import GameEngine
from src.game.enums import ActionType
from src.game.models import Action, GameConfig
from src.game.setup import setup_game


def test_playing_starting_sign_gives_power() -> None:
    state, database = setup_game(GameConfig(player_count=2, seed=4))
    engine = GameEngine(state, database)
    player = state.current_player
    sign_id = database.starter_cards["Знак"]
    player.hand = [sign_id]

    engine.step(Action(ActionType.PLAY_CARD, card_id=sign_id))

    assert player.power == 1
    assert sign_id in player.played


def test_end_turn_discards_and_draws_new_hand() -> None:
    state, database = setup_game(GameConfig(player_count=2, seed=5))
    engine = GameEngine(state, database)
    player = state.current_player

    engine.step(Action(ActionType.END_TURN))

    assert player.power == 0
    assert len(player.hand) == 5
    assert state.current_player_index == 1
