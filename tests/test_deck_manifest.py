from __future__ import annotations

from src.game.data import load_card_database
from src.game.deck_manifest import (
    EXPECTED_DOUBLE_PHYSICAL_COUNT,
    EXPECTED_DOUBLE_UNIQUE_COUNT,
    EXPECTED_MAIN_DECK_PHYSICAL_COUNT,
    EXPECTED_MAYHEM_UNIQUE_COUNT,
    EXPECTED_SINGLETON_NON_MAYHEM_COUNT,
    dead_wizard_token_count,
    load_deck_manifest,
    validate_deck_manifest,
    validate_main_deck_manifest,
)
from src.game.instances import card_id_for
from src.game.models import GameConfig
from src.game.setup import setup_game


def test_deck_manifest_loads() -> None:
    manifest = load_deck_manifest()

    assert manifest.main_deck
    assert manifest.wild_magic_quantity == 16
    assert manifest.weak_wand_quantity == 16


def test_deck_manifest_references_existing_cards() -> None:
    database = load_card_database()

    assert validate_deck_manifest(database.manifest, database) == []


def test_setup_uses_quantities() -> None:
    state, database = setup_game(GameConfig(player_count=2, seed=40))
    expected_main = sum(entry.quantity for entry in database.manifest.main_deck)
    visible_main = len(state.main_deck) + len(state.market) + len(state.mayhem_discard)

    assert visible_main == expected_main


def test_starter_deck_exact_composition() -> None:
    state, database = setup_game(GameConfig(player_count=2, seed=41))
    player = state.players[0]
    refs = player.deck + player.hand
    ids = [card_id_for(state, ref) for ref in refs]

    assert ids.count(database.starter_cards["Знак"]) == 6
    assert ids.count(database.starter_cards["Палочка"]) == 1
    assert ids.count(database.starter_cards["Пшик"]) == 3


def test_dead_wizard_tokens_player_count_times_four() -> None:
    state, database = setup_game(GameConfig(player_count=5, seed=42))

    assert dead_wizard_token_count(database.manifest, 5) == 20
    assert len(state.dead_wizard_stack) == 20


def test_wild_magic_and_weak_wand_counts() -> None:
    state, _database = setup_game(GameConfig(player_count=3, seed=43))

    assert len(state.wild_magic_stack) == 16
    assert len(state.weak_wand_stack) == 16


def test_main_deck_manifest_matches_physical_deck_rules() -> None:
    database = load_card_database()
    summary = validate_main_deck_manifest(database.manifest, database)

    assert summary["errors"] == []
    assert summary["main_deck_physical_count"] == EXPECTED_MAIN_DECK_PHYSICAL_COUNT
    assert len(summary["mayhem"]) == EXPECTED_MAYHEM_UNIQUE_COUNT
    assert len(summary["singleton_non_mayhem"]) == EXPECTED_SINGLETON_NON_MAYHEM_COUNT
    assert len(summary["double"]) == EXPECTED_DOUBLE_UNIQUE_COUNT
    assert summary["double_physical_count"] == EXPECTED_DOUBLE_PHYSICAL_COUNT


def test_game_config_no_longer_overrides_manifest_counts() -> None:
    config = GameConfig()

    assert not hasattr(config, "weak_wand_count")
    assert not hasattr(config, "wild_magic_count")
    assert not hasattr(config, "dead_wizard_token_limit")
