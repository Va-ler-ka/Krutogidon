from __future__ import annotations

from src.game.engine import GameEngine
from src.game.enums import ActionType
from src.game.instances import card_id_for, create_card_instance
from src.game.models import Action, GameConfig
from src.game.setup import setup_game


def test_card_instances_are_unique() -> None:
    state, _database = setup_game(GameConfig(player_count=2, seed=44))

    assert len(state.card_instances) == len(set(state.card_instances))


def test_two_copies_same_card_have_different_instance_ids() -> None:
    state, database = setup_game(GameConfig(player_count=2, seed=45))
    sign_id = database.starter_cards["Знак"]
    copies = [ref for ref in state.players[0].deck + state.players[0].hand if card_id_for(state, ref) == sign_id]

    assert len(copies) == 6
    assert len(set(copies)) == 6


def test_buy_moves_specific_instance_to_discard() -> None:
    state, database = setup_game(GameConfig(player_count=2, seed=46))
    engine = GameEngine(state, database)
    player = state.current_player
    instance_id = state.market[0]
    player.power = 99

    engine.step(Action(ActionType.BUY_MARKET_CARD, instance_id=instance_id, market_index=0))

    assert instance_id in player.discard
    assert instance_id not in state.market


def test_destroy_removes_specific_instance() -> None:
    state, database = setup_game(GameConfig(player_count=2, seed=47))
    instance_id = create_card_instance(state, database.starter_cards["Пшик"], owner_id=0, origin="test")
    player = state.players[0]
    player.hand = [instance_id]
    player.destroyed.append(player.hand.pop())

    assert instance_id in player.destroyed
    assert instance_id not in player.hand


def test_legal_actions_reference_specific_cards() -> None:
    state, database = setup_game(GameConfig(player_count=2, seed=48))
    engine = GameEngine(state, database)

    play_actions = [action for action in engine.legal_actions() if action.type == ActionType.PLAY_CARD]

    assert play_actions
    assert all(action.instance_id for action in play_actions)
