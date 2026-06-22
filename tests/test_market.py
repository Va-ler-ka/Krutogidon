from __future__ import annotations

from src.game.engine import GameEngine
from src.game.enums import ActionType
from src.game.instances import card_def_for
from src.game.models import Action, GameConfig
from src.game.setup import setup_game


def test_buying_market_card_refills_market() -> None:
    state, database = setup_game(GameConfig(player_count=2, seed=2))
    engine = GameEngine(state, database)
    player = state.current_player
    first_card = state.market[0]
    player.power = card_def_for(state, database, first_card).cost or 0

    engine.step(Action(ActionType.BUY_CARD, card_id=first_card, market_index=0))

    assert first_card in player.discard
    assert len(state.market) == state.config.market_size
    assert first_card not in state.market


def test_market_never_contains_mayhem_after_refill() -> None:
    state, database = setup_game(GameConfig(player_count=2, seed=3))
    engine = GameEngine(state, database)

    for _ in range(20):
        if state.game_over:
            break
        player = state.current_player
        for index, card_id in enumerate(list(state.market)):
            player.power = 99
            engine.step(Action(ActionType.BUY_CARD, card_id=card_id, market_index=0))

    assert all(card_def_for(state, database, card_id).card_class != "Беспредел" for card_id in state.market)
