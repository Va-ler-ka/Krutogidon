from __future__ import annotations

import json
import random

import pytest

from src.agents.random_agent import RandomAgent
from src.game.effects import DiscardCards
from src.game.engine import GameEngine
from src.game.enums import ActionType, GamePhase
from src.game.instances import create_card_instance
from src.game.models import Action, GameConfig, PendingChoice, PendingChoiceType, SourceKind
from src.game.serialization import state_to_json
from src.game.setup import setup_game


def test_pending_choice_serializes() -> None:
    state, database = setup_game(GameConfig(player_count=2, seed=101))
    card = create_card_instance(state, database.by_name("Знак").id, owner_id=0, origin="test")
    state.pending_choice = PendingChoice(
        choice_type=PendingChoiceType.DISCARD_CARD,
        actor_id=0,
        choice_id="choice_test",
        source_kind=SourceKind.SYSTEM,
        options=[{"id": "discard_0", "instance_id": card, "card_id": database.by_name("Знак").id}],
    )

    payload = json.loads(state_to_json(state))

    assert payload["pending_choice"]["choice_id"] == "choice_test"
    assert payload["pending_choice"]["options"][0]["instance_id"] == card


def test_legal_actions_generated_from_pending_choice() -> None:
    state, database = setup_game(GameConfig(player_count=2, seed=102))
    player = state.players[0]
    player.hand = player.hand[:2]
    state.phase = GamePhase.CHOOSE_TARGET
    state.pending_choice = PendingChoice(
        choice_type=PendingChoiceType.DISCARD_CARD,
        actor_id=player.id,
        choice_id="choice_discard",
        source_kind=SourceKind.SYSTEM,
        options=[
            {"id": f"discard_{index}", "instance_id": instance_id, "card_id": database.cards[next(iter(database.cards))].id}
            for index, instance_id in enumerate(player.hand)
        ],
    )
    engine = GameEngine(state, database)

    actions = engine.legal_actions()

    assert len(actions) == 2
    assert all(action.type == ActionType.CHOOSE_TARGET for action in actions)
    assert {action.payload["option_id"] for action in actions} == {"discard_0", "discard_1"}


def test_random_agent_resolves_pending_choice() -> None:
    state, database = setup_game(GameConfig(player_count=2, seed=103))
    engine = GameEngine(state, database)
    player = state.players[0]
    player.hand = player.hand[:2]

    DiscardCards("self", 1).apply(state=state, player=player, card=None, rng=random.Random(1), database=database)
    action = RandomAgent(seed=1).choose_action(state, engine.legal_actions(), database)
    selected = action.instance_id
    engine.step(action)

    assert selected in player.discard
    assert state.pending_choice is None


def test_pending_choice_resolution_logged() -> None:
    state, database = setup_game(GameConfig(player_count=2, seed=104))
    engine = GameEngine(state, database)
    player = state.players[0]
    player.hand = player.hand[:2]

    DiscardCards("self", 1).apply(state=state, player=player, card=None, rng=random.Random(1), database=database)
    engine.step(engine.legal_actions()[0])

    assert any("pending_choice_resolved" in event for event in state.event_log)


def test_illegal_pending_choice_option_rejected() -> None:
    state, database = setup_game(GameConfig(player_count=2, seed=105))
    engine = GameEngine(state, database)
    player = state.players[0]
    player.hand = player.hand[:2]

    DiscardCards("self", 1).apply(state=state, player=player, card=None, rng=random.Random(1), database=database)

    with pytest.raises(ValueError):
        engine.step(
            Action(
                ActionType.CHOOSE_TARGET,
                actor_id=player.id,
                instance_id=player.hand[0],
                payload={"option_id": "not_an_option"},
            )
        )
