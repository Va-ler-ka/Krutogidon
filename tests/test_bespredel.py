from __future__ import annotations

import random

from src.game.instances import create_card_instance
from src.game.mayhem import resolve_mayhem
from src.game.models import GameConfig, SourceKind
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


def test_market_mayhem_has_neutral_source_and_no_trophy() -> None:
    state, database = setup_game(GameConfig(player_count=2, seed=94))
    mayhem = next(card for card in database.mayhem_cards if "урон" in card.text.lower())
    instance_id = create_card_instance(state, mayhem.id, origin="test_mayhem")
    for player in state.players:
        player.hand = []
    state.players[1].health = 1

    resolve_mayhem(state, database, instance_id, random.Random(1), source_kind=SourceKind.MARKET_MAYHEM)

    assert state.trophy_controller_id is None
    assert any(f"source_kind={SourceKind.MARKET_MAYHEM.value}" in event for event in state.event_log)


def test_player_played_mayhem_can_award_trophy() -> None:
    state, database = setup_game(GameConfig(player_count=2, seed=95))
    mayhem = next(card for card in database.mayhem_cards if "урон" in card.text.lower())
    instance_id = create_card_instance(state, mayhem.id, owner_id=0, origin="test_mayhem")
    for player in state.players:
        player.hand = []
    state.players[1].health = 1

    resolve_mayhem(
        state,
        database,
        instance_id,
        random.Random(1),
        source_kind=SourceKind.PLAYER_MAYHEM,
        source_player_id=0,
    )

    assert state.trophy_controller_id == 0
