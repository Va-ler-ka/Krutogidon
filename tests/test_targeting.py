from __future__ import annotations

from src.game.models import GameConfig
from src.game.setup import setup_game
from src.game.targeting import LEFT_ENEMY, RIGHT_ENEMY, STRONGEST_ENEMY, WEAKEST_ENEMY, target_candidates


def test_left_and_right_enemy_do_not_duplicate_in_two_player_game() -> None:
    state, _database = setup_game(GameConfig(player_count=2, seed=24))

    assert target_candidates(state, 0, LEFT_ENEMY) == [1]
    assert target_candidates(state, 0, RIGHT_ENEMY) == [1]


def test_weakest_and_strongest_return_tied_candidates() -> None:
    state, _database = setup_game(GameConfig(player_count=3, seed=25))
    state.players[1].health = 10
    state.players[2].health = 10

    assert target_candidates(state, 0, WEAKEST_ENEMY) == [1, 2]
    assert target_candidates(state, 0, STRONGEST_ENEMY) == [1, 2]
