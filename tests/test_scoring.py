from __future__ import annotations

from src.game.models import GameConfig
from src.game.scoring import compute_winners, score_player
from src.game.setup import setup_game


def test_scoring_counts_victory_points_in_zones() -> None:
    state, database = setup_game(GameConfig(player_count=2, seed=8))
    player = state.players[0]
    card = next(card for card in database.cards.values() if card.victory_points > 1)
    player.deck = [card.id]
    player.hand = []
    player.discard = []
    player.played = []
    player.ongoing = []

    assert score_player(player, database) == card.victory_points


def test_compute_winners_uses_score() -> None:
    state, database = setup_game(GameConfig(player_count=2, seed=9))
    good_card = next(card for card in database.cards.values() if card.victory_points > 1)
    state.players[0].deck = [good_card.id]
    state.players[0].hand = []
    state.players[0].discard = []
    state.players[1].deck = []
    state.players[1].hand = []
    state.players[1].discard = []

    assert compute_winners(state, database) == [0]


def test_dead_wizard_token_penalty_zero() -> None:
    state, database = setup_game(GameConfig(player_count=2, seed=78))
    player = state.players[0]
    player.deck = []
    player.hand = []
    player.discard = []
    player.played = []
    player.ongoing = []
    player.dead_wizard_tokens = []

    assert score_player(player, database, state) == 0


def test_dead_wizard_token_penalty_one_is_minus_three() -> None:
    state, database = setup_game(GameConfig(player_count=2, seed=79))
    player = state.players[0]
    player.deck = []
    player.hand = []
    player.discard = []
    player.played = []
    player.ongoing = []
    player.dead_wizard_tokens = ["dead_1"]

    assert score_player(player, database, state) == -3


def test_dead_wizard_token_penalty_two_is_minus_six() -> None:
    state, database = setup_game(GameConfig(player_count=2, seed=80))
    player = state.players[0]
    player.deck = []
    player.hand = []
    player.discard = []
    player.played = []
    player.ongoing = []
    player.dead_wizard_tokens = ["dead_1", "dead_2"]

    assert score_player(player, database, state) == -6


def test_dead_wizard_token_tiebreaker_fewer_tokens_wins() -> None:
    state, database = setup_game(GameConfig(player_count=2, seed=81))
    for player in state.players:
        player.deck = []
        player.hand = []
        player.discard = []
        player.played = []
        player.ongoing = []
    bonus_card = next(card for card in database.cards.values() if card.victory_points == 3)
    state.players[0].deck = [bonus_card.id]
    state.players[0].dead_wizard_tokens = ["dead_1"]
    state.players[1].dead_wizard_tokens = []

    assert score_player(state.players[0], database, state) == score_player(state.players[1], database, state)
    assert compute_winners(state, database) == [1]
