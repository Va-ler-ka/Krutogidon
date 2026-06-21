from __future__ import annotations

from src.game.models import GameConfig
from src.game.setup import setup_game


def test_setup_creates_players_starting_decks_and_market() -> None:
    state, database = setup_game(GameConfig(player_count=3, seed=1))

    assert len(state.players) == 3
    assert all(player.health == 20 for player in state.players)
    assert all(len(player.hand) == 5 for player in state.players)
    assert all(len(player.deck) == 5 for player in state.players)
    assert len(state.market) == 5
    assert state.current_legend is not None
    assert all(database.cards[card_id].card_class != "Беспредел" for card_id in state.market)


def test_setup_rejects_invalid_player_count() -> None:
    try:
        setup_game(GameConfig(player_count=1))
    except ValueError as error:
        assert "player_count" in str(error)
    else:
        raise AssertionError("Expected invalid player count to raise")
