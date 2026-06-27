from __future__ import annotations

from src.game.engine import GameEngine
from src.game.enums import ActionType, GamePhase
from src.game.effects import apply_damage
from src.game.instances import create_card_instance
from src.game.models import Action, EffectRequest, GameConfig, PendingChoiceType, SourceKind
from src.game.setup import setup_game


def test_player_receives_dead_wizard_token_on_death() -> None:
    state, database = setup_game(GameConfig(player_count=2, seed=32))
    engine = GameEngine(state, database)
    wand_id = database.starter_cards["Палочка"]
    attacker = state.players[0]
    target = state.players[1]
    attacker.hand = [wand_id]
    target.health = 1

    engine.step(Action(ActionType.PLAY_CARD, card_id=wand_id, target_player=target.id))

    assert len(target.dead_wizard_tokens) == 1
    assert target.health == state.config.death_reset_health


def test_empty_dead_wizard_stack_ends_game_on_death() -> None:
    state, database = setup_game(GameConfig(player_count=2, seed=33))
    engine = GameEngine(state, database)
    wand_id = database.starter_cards["Палочка"]
    state.dead_wizard_stack = []
    state.players[0].hand = [wand_id]
    state.players[1].health = 1

    engine.step(Action(ActionType.PLAY_CARD, card_id=wand_id, target_player=1))

    assert state.game_over is True
    assert state.phase == GamePhase.GAME_OVER
    assert state.end_reason == "dead_wizard_tokens_empty"


def test_death_event_logged_without_rule_todo() -> None:
    state, database = setup_game(GameConfig(player_count=2, seed=85))
    engine = GameEngine(state, database)
    wand_id = database.starter_cards["Палочка"]
    state.players[0].hand = [wand_id]
    state.players[1].health = 1

    engine.step(Action(ActionType.PLAY_CARD, card_id=wand_id, target_player=1))

    assert any("dies and receives dead wizard token" in event for event in state.event_log)
    assert not any("TODO_RULE_CLARIFICATION" in event for event in state.event_log)


def test_trophy_awarded_when_player_kills_enemy_with_card() -> None:
    state, _database = setup_game(GameConfig(player_count=2, seed=86))
    state.players[1].health = 1
    request = EffectRequest(
        source_card_id="test_card",
        source_player_id=0,
        effect_type="deal_damage",
        amount=1,
        target_player_ids=[1],
        source_kind=SourceKind.PLAYER_CARD,
    )

    apply_damage(state, 1, 1, request)

    assert state.trophy_controller_id == 0


def test_trophy_not_awarded_on_self_kill() -> None:
    state, _database = setup_game(GameConfig(player_count=2, seed=87))
    state.players[0].health = 1
    request = EffectRequest(
        source_card_id="test_card",
        source_player_id=0,
        effect_type="deal_damage",
        amount=1,
        target_player_ids=[0],
        source_kind=SourceKind.SELF,
    )

    apply_damage(state, 0, 1, request)

    assert state.trophy_controller_id is None


def test_trophy_not_awarded_on_legend_group_attack_death() -> None:
    state, _database = setup_game(GameConfig(player_count=2, seed=88))
    state.players[1].health = 1
    request = EffectRequest(
        source_card_id="legend",
        source_player_id=None,
        effect_type="deal_damage",
        amount=1,
        target_player_ids=[1],
        source_kind=SourceKind.LEGEND_GROUP_ATTACK,
    )

    apply_damage(state, 1, 1, request)

    assert state.trophy_controller_id is None


def test_trophy_awarded_on_player_played_mayhem_kill() -> None:
    state, _database = setup_game(GameConfig(player_count=2, seed=89))
    state.players[1].health = 1
    request = EffectRequest(
        source_card_id="mayhem",
        source_player_id=0,
        effect_type="deal_damage",
        amount=1,
        target_player_ids=[1],
        source_kind=SourceKind.PLAYER_MAYHEM,
    )

    apply_damage(state, 1, 1, request)

    assert state.trophy_controller_id == 0


def test_trophy_controller_draws_six_creates_discard_choice_at_end_turn() -> None:
    state, database = setup_game(GameConfig(player_count=2, seed=96))
    engine = GameEngine(state, database)
    player = state.players[0]
    state.trophy_controller_id = player.id
    player.hand = []
    player.played = []
    player.discard = []
    player.deck = trophy_test_deck(state, database, player.id)

    engine.step(Action(ActionType.END_TURN))

    assert len(player.hand) == 6
    assert player.discard == []
    assert state.pending_choice is not None
    assert state.pending_choice.choice_type == PendingChoiceType.TROPHY_DISCARD
    assert len(state.pending_choice.options) == 6
    assert any("pending_choice_created: trophy_discard" in event for event in state.event_log)


def test_trophy_discard_moves_selected_card_and_continues_turn() -> None:
    state, database = setup_game(GameConfig(player_count=2, seed=96))
    engine = GameEngine(state, database)
    player = state.players[0]
    state.trophy_controller_id = player.id
    player.hand = []
    player.played = []
    player.discard = []
    player.deck = trophy_test_deck(state, database, player.id)

    engine.step(Action(ActionType.END_TURN))
    action = engine.legal_actions()[0]
    selected = action.instance_id
    engine.step(action)

    assert selected in player.discard
    assert selected not in player.hand
    assert state.pending_choice is None
    assert state.current_player_index == 1
    assert state.phase == GamePhase.MAIN
    assert any("trophy_discard" in event for event in state.event_log)


def trophy_test_deck(state, database, player_id: int) -> list[str]:
    return [
        create_card_instance(state, database.by_name("Знак").id, owner_id=player_id, origin="test_trophy"),
        create_card_instance(state, database.by_name("Знак").id, owner_id=player_id, origin="test_trophy"),
        create_card_instance(state, database.by_name("Знак").id, owner_id=player_id, origin="test_trophy"),
        create_card_instance(state, database.by_name("Знак").id, owner_id=player_id, origin="test_trophy"),
        create_card_instance(state, database.by_name("Пшик").id, owner_id=player_id, origin="test_trophy"),
        create_card_instance(state, database.by_name("Пшик").id, owner_id=player_id, origin="test_trophy"),
    ]
