from __future__ import annotations

from src.game.models import GameConfig
from src.game.setup import setup_game
from src.game.targeting import (
    ALL_WIZARDS,
    CHOSEN_WIZARD,
    LEFT_ENEMY,
    LEFT_OR_RIGHT_ENEMY,
    RIGHT_ENEMY,
    STRONGEST_ENEMY,
    WEAKEST_ENEMY,
    parse_selector_from_text,
    target_candidates,
)


def test_left_and_right_enemy_do_not_duplicate_in_two_player_game() -> None:
    state, _database = setup_game(GameConfig(player_count=2, seed=24))

    assert target_candidates(state, 0, LEFT_ENEMY) == [1]
    assert target_candidates(state, 0, RIGHT_ENEMY) == [1]
    assert target_candidates(state, 0, LEFT_OR_RIGHT_ENEMY) == [1]


def test_weakest_and_strongest_return_tied_candidates() -> None:
    state, _database = setup_game(GameConfig(player_count=3, seed=25))
    state.players[1].health = 10
    state.players[2].health = 10

    assert target_candidates(state, 0, WEAKEST_ENEMY) == [1, 2]
    assert target_candidates(state, 0, STRONGEST_ENEMY) == [1, 2]


def test_chosen_wizard_can_target_self() -> None:
    state, _database = setup_game(GameConfig(player_count=3, seed=70))

    assert target_candidates(state, 0, CHOSEN_WIZARD) == [0, 1, 2]


def test_all_wizards_targets_every_player() -> None:
    state, _database = setup_game(GameConfig(player_count=4, seed=71))

    assert target_candidates(state, 2, ALL_WIZARDS) == [0, 1, 2, 3]


def test_parse_selector_from_common_card_text() -> None:
    assert parse_selector_from_text("нанеси 1 урон выбранному колдуну") == CHOSEN_WIZARD
    assert parse_selector_from_text("нанеси 1 урон каждому колдуну") == ALL_WIZARDS
    assert parse_selector_from_text("нанеси 1 урон правому или левому врагу") == LEFT_OR_RIGHT_ENEMY
