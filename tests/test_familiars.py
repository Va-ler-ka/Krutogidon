from __future__ import annotations

from src.game.engine import GameEngine
from src.game.enums import ActionType
from src.game.instances import card_id_for, create_card_instance
from src.game.models import Action, GameConfig
from src.game.setup import setup_game


def test_familiar_starts_unbought() -> None:
    state, _database = setup_game(GameConfig(player_count=2, seed=51))

    assert state.players[0].unbought_familiar_id is not None
    assert state.players[0].familiar_purchased is False


def test_unbought_familiar_effects_do_not_apply() -> None:
    state, _database = setup_game(GameConfig(player_count=2, seed=52))

    assert state.players[0].unbought_familiar_id not in state.players[0].hand


def test_buy_familiar_puts_card_into_discard() -> None:
    state, database = setup_game(GameConfig(player_count=2, seed=53))
    engine = GameEngine(state, database)
    player = state.current_player
    familiar_id = player.unbought_familiar_id
    player.power = 99

    engine.step(Action(ActionType.BUY_FAMILIAR, card_id=familiar_id))

    assert player.familiar_purchased is True
    assert any(card_id_for(state, ref) == familiar_id for ref in player.discard)


def test_familiar_cannot_be_bought_twice() -> None:
    state, database = setup_game(GameConfig(player_count=2, seed=54))
    engine = GameEngine(state, database)
    player = state.current_player
    player.power = 99
    engine.step(Action(ActionType.BUY_FAMILIAR, card_id=player.unbought_familiar_id))
    player.power = 99

    try:
        engine.step(Action(ActionType.BUY_FAMILIAR, card_id=player.unbought_familiar_id))
    except ValueError as error:
        assert "Illegal action" in str(error)
    else:
        raise AssertionError("Expected second familiar purchase to be illegal")


def test_familiar_defense_requires_card_in_hand() -> None:
    state, database = setup_game(GameConfig(player_count=2, seed=55))
    engine = GameEngine(state, database)
    wand = database.starter_cards["Палочка"]
    familiar = next(card for card in database.cards.values() if card.card_class == "Фамильяр" and card.defense)
    state.players[0].hand = [create_card_instance(state, wand, owner_id=0, origin="test")]
    state.players[1].unbought_familiar_id = familiar.id
    state.players[1].hand = []

    engine.step(Action(ActionType.PLAY_CARD, instance_id=state.players[0].hand[0], target_player=1))

    assert all(action.type != ActionType.USE_DEFENSE for action in engine.legal_actions())
