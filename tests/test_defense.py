from __future__ import annotations

from src.game.engine import GameEngine
from src.game.enums import ActionType, GamePhase
from src.game.models import Action, GameConfig
from src.game.setup import setup_game


def first_defense_card(database) -> str:
    return next(card.id for card in database.cards.values() if card.defense)


def first_familiar_defense(database) -> str:
    return next(card.id for card in database.cards.values() if card.card_class == "Фамильяр" and card.defense)


def test_attack_opens_defense_window_and_defense_prevents_damage() -> None:
    state, database = setup_game(GameConfig(player_count=2, seed=26))
    engine = GameEngine(state, database)
    wand_id = database.starter_cards["Палочка"]
    defense_id = first_defense_card(database)
    attacker = state.players[0]
    defender = state.players[1]
    attacker.hand = [wand_id]
    defender.hand = [defense_id]

    engine.step(Action(ActionType.PLAY_CARD, card_id=wand_id, target_player=defender.id))

    assert state.phase == GamePhase.DEFENSE_WINDOW
    assert defender.health == 20

    engine.step(Action(ActionType.USE_DEFENSE, card_id=defense_id, actor_id=defender.id))

    assert defender.health == 20
    assert defense_id in defender.discard
    assert state.phase == GamePhase.MAIN


def test_declining_defense_allows_damage() -> None:
    state, database = setup_game(GameConfig(player_count=2, seed=27))
    engine = GameEngine(state, database)
    wand_id = database.starter_cards["Палочка"]
    defense_id = first_defense_card(database)
    attacker = state.players[0]
    defender = state.players[1]
    attacker.hand = [wand_id]
    defender.hand = [defense_id]

    engine.step(Action(ActionType.PLAY_CARD, card_id=wand_id, target_player=defender.id))
    engine.step(Action(ActionType.DECLINE_DEFENSE, actor_id=defender.id))

    assert defender.health == 19
    assert state.phase == GamePhase.MAIN


def test_familiar_defense_redirects_damage_to_attacker() -> None:
    state, database = setup_game(GameConfig(player_count=2, seed=28))
    engine = GameEngine(state, database)
    wand_id = database.starter_cards["Палочка"]
    familiar_id = first_familiar_defense(database)
    attacker = state.players[0]
    defender = state.players[1]
    attacker.hand = [wand_id]
    defender.hand = []
    defender.familiar = familiar_id

    engine.step(Action(ActionType.PLAY_CARD, card_id=wand_id, target_player=defender.id))
    engine.step(
        Action(
            ActionType.USE_DEFENSE,
            card_id=familiar_id,
            actor_id=defender.id,
            payload={"defense_source": "familiar"},
        )
    )

    assert defender.health == 20
    assert attacker.health == 19
    assert defender.familiar is None
