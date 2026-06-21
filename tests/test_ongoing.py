from __future__ import annotations

from src.game.engine import GameEngine
from src.game.enums import ActionType
from src.game.models import Action, GameConfig
from src.game.setup import setup_game


def test_ongoing_card_stays_in_play_after_end_turn() -> None:
    state, database = setup_game(GameConfig(player_count=2, seed=29))
    engine = GameEngine(state, database)
    ongoing_id = next(card.id for card in database.cards.values() if card.ongoing)
    player = state.current_player
    player.hand = [ongoing_id]

    engine.step(Action(ActionType.PLAY_CARD, card_id=ongoing_id))
    engine.step(Action(ActionType.END_TURN))

    assert ongoing_id in player.ongoing
    assert ongoing_id not in player.discard


def test_non_ongoing_card_goes_to_discard_after_end_turn() -> None:
    state, database = setup_game(GameConfig(player_count=2, seed=30))
    engine = GameEngine(state, database)
    sign_id = database.starter_cards["Знак"]
    player = state.current_player
    player.hand = [sign_id]

    engine.step(Action(ActionType.PLAY_CARD, card_id=sign_id))
    engine.step(Action(ActionType.END_TURN))

    assert sign_id in player.discard
