from __future__ import annotations

import random

from src.game.instances import create_card_instance
from src.game.engine import GameEngine
from src.game.enums import ActionType, GamePhase
from src.game.mayhem import resolve_mayhem
from src.game.models import GameConfig, PendingChoiceType, SourceKind
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


def test_bespredel_10_detects_attack_cards_in_market() -> None:
    state, database = setup_game(GameConfig(player_count=2, seed=110))
    state.market = [
        create_card_instance(state, database.by_name("Грешок-потрошок").id, origin="test_market"),
        create_card_instance(state, database.by_name("Знак").id, origin="test_market"),
    ]
    instance_id = create_card_instance(state, "беспредел_10", origin="test_mayhem")
    for player in state.players:
        player.hand = []

    resolve_mayhem(state, database, instance_id, random.Random(1), source_kind=SourceKind.MARKET_MAYHEM)

    assert state.players[1].health == 15
    assert any("mayhem_handler_used: беспредел_10" in event for event in state.event_log)


def test_bespredel_10_plays_only_attack_sections() -> None:
    state, database = setup_game(GameConfig(player_count=2, seed=111))
    state.market = [create_card_instance(state, database.by_name("Солнцеликий").id, origin="test_market")]
    instance_id = create_card_instance(state, "беспредел_10", origin="test_mayhem")
    active = state.players[0]
    for player in state.players:
        player.hand = []
    before_hand = len(active.hand)
    before_power = active.power

    resolve_mayhem(state, database, instance_id, random.Random(1), source_kind=SourceKind.MARKET_MAYHEM)

    assert active.power == before_power
    assert len(active.hand) == before_hand
    assert state.players[1].health == 10


def test_bespredel_10_death_does_not_award_trophy() -> None:
    state, database = setup_game(GameConfig(player_count=2, seed=112))
    state.market = [create_card_instance(state, database.by_name("Солнцеликий").id, origin="test_market")]
    instance_id = create_card_instance(state, "беспредел_10", origin="test_mayhem")
    for player in state.players:
        player.hand = []
    state.players[1].health = 1

    resolve_mayhem(state, database, instance_id, random.Random(1), source_kind=SourceKind.MARKET_MAYHEM)

    assert state.trophy_controller_id is None
    assert any(f"source_kind={SourceKind.MARKET_MAYHEM.value}" in event for event in state.event_log)


def test_bespredel_10_allows_defense_and_ignores_redirect_without_attacker() -> None:
    state, database = setup_game(GameConfig(player_count=2, seed=113))
    engine = GameEngine(state, database)
    state.market = [create_card_instance(state, database.by_name("Солнцеликий").id, origin="test_market")]
    instance_id = create_card_instance(state, "беспредел_10", origin="test_mayhem")
    redirect_defense = create_card_instance(
        state,
        database.by_name("Лобковое отродье").id,
        owner_id=1,
        origin="test_defense",
    )
    state.players[0].hand = []
    state.players[1].hand = [redirect_defense]
    active_health = state.players[0].health

    resolve_mayhem(state, database, instance_id, random.Random(1), source_kind=SourceKind.MARKET_MAYHEM)

    assert state.phase == GamePhase.DEFENSE_WINDOW
    defense_action = next(action for action in engine.legal_actions() if action.type == ActionType.USE_DEFENSE)
    engine.step(defense_action)
    assert state.players[0].health == active_health
    assert any("redirect ignored" in event for event in state.event_log)


def test_bespredel_10_target_choice_uses_pending_choice() -> None:
    state, database = setup_game(GameConfig(player_count=3, seed=114))
    state.market = [create_card_instance(state, database.by_name("Солнцеликий").id, origin="test_market")]
    instance_id = create_card_instance(state, "беспредел_10", origin="test_mayhem")
    for player in state.players:
        player.hand = []

    resolve_mayhem(state, database, instance_id, random.Random(1), source_kind=SourceKind.MARKET_MAYHEM)

    assert state.phase == GamePhase.CHOOSE_TARGET
    assert state.pending_choice is not None
    assert state.pending_choice.choice_type == PendingChoiceType.CHOOSE_MARKET_ATTACK_TARGET
    assert state.pending_choice.source_kind == SourceKind.MARKET_MAYHEM
    assert len(state.pending_choice.options) == 2


def test_bespredel_10_strict_fails_on_unparseable_market_attack() -> None:
    state, database = setup_game(GameConfig(player_count=2, seed=115, strict=True))
    state.market = [create_card_instance(state, database.by_name("Бедовая принцесса").id, origin="test_market")]
    instance_id = create_card_instance(state, "беспредел_10", origin="test_mayhem")

    try:
        resolve_mayhem(state, database, instance_id, random.Random(1), source_kind=SourceKind.MARKET_MAYHEM)
    except NotImplementedError as exc:
        assert "волшебник_бедовая_принцесса" in str(exc)
    else:
        raise AssertionError("Expected strict mode to reject dynamic market attack")


def test_bespredel_10_non_strict_logs_partial_unsafe_for_unparseable_market_attack() -> None:
    state, database = setup_game(GameConfig(player_count=2, seed=116))
    state.market = [create_card_instance(state, database.by_name("Бедовая принцесса").id, origin="test_market")]
    instance_id = create_card_instance(state, "беспредел_10", origin="test_mayhem")

    resolve_mayhem(state, database, instance_id, random.Random(1), source_kind=SourceKind.MARKET_MAYHEM)

    assert any("partial_unsafe market attack not implemented" in event for event in state.event_log)
