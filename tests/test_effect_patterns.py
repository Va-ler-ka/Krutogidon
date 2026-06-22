from __future__ import annotations

import random

from src.game.effects import ConditionalEffect, DestroyCard, DrawCards, GainCard, GiveWeakWand, Heal, parse_basic_effect
from src.game.instances import create_card_instance
from src.game.models import CardDefinition, GameConfig
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


def test_heal_under_cap() -> None:
    state, database = setup_game(GameConfig(player_count=2, seed=82))
    player = state.players[0]
    player.health = 18

    Heal(3).apply(state=state, player=player, card=None, rng=random.Random(1), database=database)

    assert player.health == 21


def test_heal_to_cap() -> None:
    state, database = setup_game(GameConfig(player_count=2, seed=83))
    player = state.players[0]
    player.health = 22

    Heal(3).apply(state=state, player=player, card=None, rng=random.Random(1), database=database)

    assert player.health == state.config.max_health


def test_heal_does_not_exceed_25() -> None:
    state, database = setup_game(GameConfig(player_count=2, seed=84))
    player = state.players[0]
    player.health = 24

    Heal(10).apply(state=state, player=player, card=None, rng=random.Random(1), database=database)

    assert player.health == 25


def test_parsed_attack_can_make_each_enemy_discard() -> None:
    state, database = setup_game(GameConfig(player_count=3, seed=76))
    card = CardDefinition(
        id="test_discard_attack",
        name="Discard Attack",
        card_class="Test",
        text="Атака: каждый враг сбрасывает 1 карту.",
        attack=True,
    )
    for player in state.players[1:]:
        player.hand = [create_card_instance(state, database.by_name("Знак").id, owner_id=player.id, origin="test")]

    parse_basic_effect(card).apply(
        state=state,
        player=state.players[0],
        card=card,
        rng=random.Random(1),
        database=database,
    )

    assert all(len(player.hand) == 0 for player in state.players[1:])
    assert all(len(player.discard) == 1 for player in state.players[1:])


def test_parsed_attack_can_give_weak_wand_to_target() -> None:
    state, database = setup_game(GameConfig(player_count=2, seed=77))
    card = CardDefinition(
        id="test_weak_wand_attack",
        name="Weak Wand Attack",
        card_class="Test",
        text="+1 мощь. Атака: нанеси выбранному врагу 3 урона, и он получает вялую палочку.",
        power=1,
        attack=True,
    )
    before_weak_wands = len(state.weak_wand_stack)

    parse_basic_effect(card, target_player=1).apply(
        state=state,
        player=state.players[0],
        card=card,
        rng=random.Random(1),
        database=database,
    )

    assert state.players[0].power == 1
    assert state.players[1].health == 17
    assert len(state.players[1].discard) == 1
    assert len(state.weak_wand_stack) == before_weak_wands - 1
