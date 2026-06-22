from __future__ import annotations

import random

from src.game.effects import ConditionalEffect, DestroyCard, DrawCards, GainCard, GiveWeakWand, Heal
from src.game.models import GameConfig
from src.game.setup import setup_game


def test_give_weak_wand() -> None:
    state, database = setup_game(GameConfig(player_count=2, seed=62))
    before = len(state.players[1].discard)

    GiveWeakWand("chosen_enemy", 1).apply(state=state, player=state.players[0], card=None, rng=random.Random(1), database=database)

    assert len(state.players[1].discard) == before + 1


def test_destroy_from_hand() -> None:
    state, database = setup_game(GameConfig(player_count=2, seed=63))
    player = state.players[0]
    player.hand = player.hand[:1]
    target = player.hand[0]

    DestroyCard("hand").apply(state=state, player=player, card=None, rng=random.Random(1), database=database)

    assert target in player.destroyed


def test_destroy_from_discard() -> None:
    state, database = setup_game(GameConfig(player_count=2, seed=64))
    player = state.players[0]
    target = player.hand.pop()
    player.discard = [target]

    DestroyCard("discard").apply(state=state, player=player, card=None, rng=random.Random(1), database=database)

    assert target in player.destroyed


def test_gain_card_from_market() -> None:
    state, database = setup_game(GameConfig(player_count=2, seed=65))
    player = state.players[0]
    target = state.market[0]

    GainCard("market").apply(state=state, player=player, card=None, rng=random.Random(1), database=database)

    assert target in player.discard


def test_next_gained_card_to_top_deck() -> None:
    state, database = setup_game(GameConfig(player_count=2, seed=66))
    player = state.players[0]
    player.next_gained_card_to_top_deck = True
    target = state.market[0]

    GainCard("market").apply(state=state, player=player, card=None, rng=random.Random(1), database=database)

    assert player.deck[-1] == target


def test_conditional_effect_then_else() -> None:
    state, database = setup_game(GameConfig(player_count=2, seed=67))
    player = state.players[0]
    before = player.health

    ConditionalEffect("unknown", DrawCards(1), Heal(2)).apply(
        state=state,
        player=player,
        card=None,
        rng=random.Random(1),
        database=database,
    )

    assert player.health == before + 2
