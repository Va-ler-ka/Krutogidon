from __future__ import annotations

import random

from src.game.models import GameConfig
from src.game.setup import fill_market, setup_game


def test_mayhem_does_not_occupy_market_slot_and_is_logged() -> None:
    state, database = setup_game(GameConfig(player_count=2, seed=31))
    state.market = []
    normal_cards = [card_id for card_id in database.main_deck_cards if database.cards[card_id].card_class != "Беспредел"]
    mayhem = database.mayhem_cards[0].id
    state.main_deck = [normal_cards[0], normal_cards[1], normal_cards[2], normal_cards[3], normal_cards[4], mayhem]

    fill_market(state, database, random.Random(31))

    assert len(state.market) == 5
    assert mayhem in state.mayhem_discard
    assert all(database.cards[card_id].card_class != "Беспредел" for card_id in state.market)
    assert any("Беспредел" in event for event in state.event_log)
