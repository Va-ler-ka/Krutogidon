from __future__ import annotations

from src.game.card_text import parse_card_text
from src.game.engine import GameEngine
from src.game.enums import ActionType
from src.game.instances import create_card_instance
from src.game.models import Action, GameConfig
from src.game.setup import setup_game


def test_parse_main_and_attack_sections() -> None:
    sections = parse_card_text("+2 мощи. Атака: нанеси 3 урон выбранному врагу.")

    assert sections.main_text == "+2 мощи."
    assert sections.attack_text == "нанеси 3 урон выбранному врагу."


def test_parse_defense_section() -> None:
    sections = parse_card_text("+1 мощь. Защита: можешь избежать атаки. Возьми 1 карту.")

    assert sections.defense_text == "можешь избежать атаки. Возьми 1 карту."


def test_parse_ongoing_section() -> None:
    sections = parse_card_text("Постоянка: В начале хода возьми 1 карту.")

    assert sections.ongoing_text == "В начале хода возьми 1 карту."


def test_parse_group_attack_section() -> None:
    sections = parse_card_text("+1 мощь. Групповая атака: каждый колдун получает вялую палочку.")

    assert sections.group_attack_text == "каждый колдун получает вялую палочку."


def test_defense_text_not_applied_on_normal_play() -> None:
    state, database = setup_game(GameConfig(player_count=2, seed=49))
    engine = GameEngine(state, database)
    defense_card = next(card for card in database.cards.values() if card.defense and "Возьми" in card.text)
    instance_id = create_card_instance(state, defense_card.id, owner_id=0, origin="test")
    player = state.players[0]
    player.hand = [instance_id]
    before = len(player.hand) + len(player.deck)

    engine.step(Action(ActionType.PLAY_CARD, instance_id=instance_id))

    assert len(player.hand) + len(player.deck) <= before


def test_attack_text_not_applied_without_attack_resolution() -> None:
    state, database = setup_game(GameConfig(player_count=2, seed=50))
    engine = GameEngine(state, database)
    attack_card = next(card for card in database.cards.values() if card.attack and "нанеси" in card.text)
    instance_id = create_card_instance(state, attack_card.id, owner_id=0, origin="test")
    state.players[0].hand = [instance_id]
    state.players[1].health = 20

    engine.step(Action(ActionType.PLAY_CARD, instance_id=instance_id, target_player=1))

    assert state.players[1].health <= 20
