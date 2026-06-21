from __future__ import annotations

from dataclasses import replace

from src.game.engine import GameEngine
from src.game.enums import ActionType
from src.game.models import Action, GameConfig
from src.game.setup import setup_game


def test_player_can_defeat_one_legend_per_turn() -> None:
    state, database = setup_game(GameConfig(player_count=2, seed=6, legend_count=2))
    engine = GameEngine(state, database)
    player = state.current_player
    legend_id = state.current_legend
    assert legend_id is not None
    player.power = database.cards[legend_id].cost or 0

    engine.step(Action(ActionType.DEFEAT_LEGEND, card_id=legend_id))

    assert legend_id in player.discard
    assert player.defeated_legends == 1
    assert player.has_defeated_legend_this_turn is True
    assert state.current_legend is None


def test_new_legend_is_revealed_at_end_of_turn() -> None:
    state, database = setup_game(GameConfig(player_count=2, seed=7, legend_count=2))
    engine = GameEngine(state, database)
    player = state.current_player
    first_legend = state.current_legend
    assert first_legend is not None
    player.power = 99
    engine.step(Action(ActionType.DEFEAT_LEGEND, card_id=first_legend))

    engine.step(Action(ActionType.END_TURN))

    assert state.current_legend is not None
    assert state.current_legend != first_legend


def test_group_attack_logs_event_and_can_open_defense_window() -> None:
    state, database = setup_game(GameConfig(player_count=2, seed=35))
    engine = GameEngine(state, database)
    legend_id = state.current_legend
    assert legend_id is not None
    database.cards[legend_id] = replace(
        database.cards[legend_id],
        text="Групповая атака: нанеси 1 урон каждому врагу.",
        group_attack=True,
    )
    defense_id = next(card.id for card in database.cards.values() if card.defense)
    state.players[1].hand = [defense_id]

    engine.resolve_group_attack(legend_id)

    assert any("Групповая атака легенды" in event for event in state.event_log)
    assert state.pending_choice is not None
