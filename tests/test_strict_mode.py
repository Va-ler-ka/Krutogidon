from __future__ import annotations

import random

from src.game.engine import GameEngine
from src.game.enums import ActionType
from src.game.instances import create_card_instance
from src.game.mayhem import resolve_mayhem
from src.game.models import Action, GameConfig
from src.game.setup import setup_game


def test_unimplemented_effect_logs_in_non_strict() -> None:
    state, database = setup_game(GameConfig(player_count=2, seed=58, strict=False))
    engine = GameEngine(state, database)
    card = next(
        card
        for card in database.cards.values()
        if card.implementation_status == "not_implemented"
        and card.text
        and all(token not in card.text.lower() for token in ["мощ", "возьми", "нанеси", "накрути"])
    )
    instance_id = create_card_instance(state, card.id, owner_id=0, origin="test")
    state.players[0].hand = [instance_id]

    engine.step(Action(ActionType.PLAY_CARD, instance_id=instance_id))

    assert any("skipped" in event or "complex text skipped" in event for event in state.event_log)


def test_unimplemented_effect_raises_in_strict() -> None:
    state, database = setup_game(GameConfig(player_count=2, seed=59, strict=True))
    engine = GameEngine(state, database)
    card = next(card for card in database.cards.values() if card.implementation_status == "not_implemented" and card.text)
    instance_id = create_card_instance(state, card.id, owner_id=0, origin="test")
    state.players[0].hand = [instance_id]

    try:
        engine.step(Action(ActionType.PLAY_CARD, instance_id=instance_id))
    except NotImplementedError:
        pass
    else:
        raise AssertionError("Expected strict mode to raise")


def test_unimplemented_group_attack_raises_in_strict() -> None:
    state, database = setup_game(GameConfig(player_count=2, seed=60, strict=True))
    engine = GameEngine(state, database)

    try:
        engine.resolve_group_attack(state.current_legend)
    except NotImplementedError:
        pass
    else:
        raise AssertionError("Expected strict group attack to raise")


def test_unimplemented_mayhem_raises_in_strict() -> None:
    state, database = setup_game(GameConfig(player_count=2, seed=61, strict=True))
    card = next(card for card in database.mayhem_cards if "Разыграй групповую атаку" in card.text)
    instance_id = create_card_instance(state, card.id, origin="test")

    try:
        resolve_mayhem(state, database, instance_id, random.Random(1))
    except NotImplementedError:
        pass
    else:
        raise AssertionError("Expected strict mayhem to raise")


def test_starter_cards_do_not_raise_in_strict() -> None:
    state, database = setup_game(GameConfig(player_count=2, seed=73, strict=True))
    engine = GameEngine(state, database)

    for card in [database.by_name("Знак"), database.by_name("Пшик")]:
        state.players[0].hand = [card.id]
        engine.step(Action(ActionType.PLAY_CARD, card_id=card.id))

    wand = database.by_name("Палочка")
    state.players[0].hand = [wand.id]
    engine.step(Action(ActionType.PLAY_CARD, card_id=wand.id, target_player=1))

    assert state.players[1].health == 19


def test_wand_draws_two_cards_when_attack_kills_target() -> None:
    state, database = setup_game(GameConfig(player_count=2, seed=74, strict=True))
    engine = GameEngine(state, database)
    attacker = state.players[0]
    defender = state.players[1]
    wand = database.by_name("Палочка")
    draw_ids = [
        create_card_instance(state, database.by_name("Знак").id, owner_id=attacker.id, origin="test"),
        create_card_instance(state, database.by_name("Пшик").id, owner_id=attacker.id, origin="test"),
    ]
    attacker.hand = [wand.id]
    attacker.deck = draw_ids[:]
    attacker.discard = []
    defender.hand = []
    defender.health = 1

    engine.step(Action(ActionType.PLAY_CARD, card_id=wand.id, target_player=defender.id))

    assert len(attacker.hand) == 2
    assert defender.dead_wizard_tokens
    assert defender.health == state.config.death_reset_health
