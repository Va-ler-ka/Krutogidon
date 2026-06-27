from __future__ import annotations

import random
import re
from collections.abc import Callable

from .card_text import parse_card_text
from .effects import resolve_damage_request
from .enums import GamePhase
from .instances import card_def_for, card_id_for
from .models import CardDatabase, EffectRequest, GameState, PendingChoice, PendingChoiceType, SourceKind
from .targeting import (
    ALL_ENEMIES,
    ALL_WIZARDS,
    CHOSEN_ENEMY,
    LEFT_ENEMY,
    RIGHT_ENEMY,
    needs_target_choice,
    parse_selector_from_text,
    target_candidates,
)


MayhemHandler = Callable[[GameState, CardDatabase, str, random.Random, SourceKind, int | None], bool]


MAYHEM_HANDLERS: dict[str, MayhemHandler] = {}


def resolve_mayhem(
    state: GameState,
    database: CardDatabase,
    instance_id: str,
    rng: random.Random,
    *,
    source_kind: SourceKind = SourceKind.MARKET_MAYHEM,
    source_player_id: int | None = None,
) -> None:
    card = card_def_for(state, database, instance_id)
    lower = card.text.lower()
    state.event_log.append(f"Беспредел раскрыт: {card.name} (source_kind={source_kind.value})")
    handler = MAYHEM_HANDLERS.get(card.id)
    if handler is not None and handler(state, database, instance_id, rng, source_kind, source_player_id):
        return
    damage_match = re.search(r"кажд(?:ый|ому|ого).*?(\d+)\s+урон", lower)
    if damage_match:
        damage = int(damage_match.group(1))
        request = EffectRequest(
            source_card_id=card.id,
            source_player_id=source_player_id,
            effect_type="deal_damage",
            amount=damage,
            target_player_ids=[player.id for player in state.players],
            is_attack=True,
            group=True,
            source_kind=source_kind,
            source_card_instance_id=instance_id,
            defense_allowed=True,
            redirectable=source_kind == SourceKind.PLAYER_MAYHEM,
        )
        resolve_damage_request(state, request, database=database, rng=rng)
        state.event_log.append(f"{card.name}: partial mayhem damage resolved")
        return
    if "получает вялую палочку" in lower or "получают вялую палочку" in lower:
        for player in state.players:
            if state.weak_wand_stack:
                player.discard.append(state.weak_wand_stack.pop())
        state.event_log.append(f"{card.name}: partial mayhem weak wand resolved")
        return
    if "сбрасывает" in lower and "карт" in lower:
        for player in state.players:
            if player.hand:
                player.discard.append(player.hand.pop())
        state.event_log.append(f"{card.name}: partial mayhem discard resolved")
        return
    if "групповую атаку текущей легенды" in lower:
        if state.config.strict:
            raise NotImplementedError(f"Mayhem current legend group attack not implemented for {card.id}: {card.text}")
        state.event_log.append(f"{card.name}: current legend group attack requested")
        return
    if state.config.strict:
        raise NotImplementedError(f"Mayhem not implemented for {card.id}: {card.text}")
    state.event_log.append(f"{card.name}: mayhem not_implemented")


def register_mayhem_handler(card_id: str) -> Callable[[MayhemHandler], MayhemHandler]:
    def decorator(handler: MayhemHandler) -> MayhemHandler:
        MAYHEM_HANDLERS[card_id] = handler
        return handler

    return decorator


@register_mayhem_handler("беспредел_10")
def play_each_market_attack_handler(
    state: GameState,
    database: CardDatabase,
    instance_id: str,
    rng: random.Random,
    source_kind: SourceKind,
    source_player_id: int | None,
) -> bool:
    mayhem = card_def_for(state, database, instance_id)
    queue: list[dict] = []
    partial_cards: list[str] = []
    for market_instance_id in list(state.market):
        market_card = card_def_for(state, database, market_instance_id)
        attack_text = parse_card_text(market_card.text).attack_text
        if not market_card.attack or not attack_text:
            continue
        items = market_attack_items(state, attack_text, market_card.id, market_instance_id)
        if items:
            queue.extend(items)
            continue
        message = (
            f"{mayhem.name}: partial_unsafe market attack not implemented "
            f"for {market_card.id}: {attack_text}"
        )
        if state.config.strict:
            raise NotImplementedError(message)
        partial_cards.append(market_card.id)
        state.event_log.append(message)

    state.event_log.append(
        f"mayhem_handler_used: {mayhem.id} handler=play_each_market_attack "
        f"market_attacks={len(queue)} partial_unsafe={len(partial_cards)} "
        f"source_kind={source_kind.value}"
    )
    if not queue:
        return True
    state.pending_market_attack_queue = queue
    continue_market_attack_queue(state, database, rng)
    return True


def market_attack_items(
    state: GameState,
    attack_text: str,
    market_card_id: str,
    market_instance_id: str,
) -> list[dict]:
    lower = attack_text.lower()
    selector = parse_market_attack_selector(lower)
    target_ids = target_candidates(state, state.current_player.id, selector)
    if "левому и правому враг" in lower:
        target_ids = sorted(
            set(
                target_candidates(state, state.current_player.id, LEFT_ENEMY)
                + target_candidates(state, state.current_player.id, RIGHT_ENEMY)
            )
        )
        selector = ALL_ENEMIES

    if is_dynamic_damage_attack(lower):
        return []
    damage_match = re.search(r"(?:нанеси|отхватывает|отхватывают).*?(\d+)\s+урон\w*", lower)
    if damage_match:
        return [
            {
                "kind": "damage",
                "market_card_id": market_card_id,
                "market_instance_id": market_instance_id,
                "amount": int(damage_match.group(1)),
                "selector": selector,
                "target_player_ids": target_ids,
            }
        ]

    if "получает вялую палочку" in lower or "получают вялую палочку" in lower:
        return [
            {
                "kind": "weak_wand",
                "market_card_id": market_card_id,
                "market_instance_id": market_instance_id,
                "target_player_ids": target_ids,
            }
        ]

    discard_match = re.search(r"сбрасывает\s+1\s+карт", lower)
    if discard_match and "стоимость" not in lower:
        return [
            {
                "kind": "discard_one",
                "market_card_id": market_card_id,
                "market_instance_id": market_instance_id,
                "target_player_id": target_id,
            }
            for target_id in target_ids
        ]

    return []


def parse_market_attack_selector(lower: str) -> str:
    if "каждый колдун" in lower or "каждому колдун" in lower:
        return ALL_WIZARDS
    if "левый враг" in lower:
        return LEFT_ENEMY
    if "правый враг" in lower:
        return RIGHT_ENEMY
    return parse_selector_from_text(lower, default=CHOSEN_ENEMY)


def is_dynamic_damage_attack(lower: str) -> bool:
    dynamic_needles = [
        "за кажд",
        "стоимость",
        "самой дорог",
        "постоянк",
        "вялую палочк",
        "легенд",
        "раскрывает",
    ]
    return "урон" in lower and any(needle in lower for needle in dynamic_needles)


def continue_market_attack_queue(state: GameState, database: CardDatabase, rng: random.Random) -> None:
    while state.pending_market_attack_queue:
        item = state.pending_market_attack_queue.pop(0)
        if item["kind"] == "damage":
            resolve_market_damage_item(state, database, rng, item)
            if state.phase in {GamePhase.DEFENSE_WINDOW, GamePhase.CHOOSE_TARGET}:
                return
            continue
        if item["kind"] == "weak_wand":
            resolve_market_weak_wand_item(state, item)
            continue
        if item["kind"] == "discard_one":
            resolve_market_discard_item(state, database, item)
            if state.phase == GamePhase.CHOOSE_TARGET:
                return
            continue
        state.event_log.append(f"market mayhem queue item not_implemented: {item}")
    state.event_log.append("mayhem_handler_completed: play_each_market_attack")


def resolve_market_damage_item(
    state: GameState,
    database: CardDatabase,
    rng: random.Random,
    item: dict,
) -> None:
    targets = list(item["target_player_ids"])
    selector = item.get("selector", CHOSEN_ENEMY)
    request = EffectRequest(
        source_card_id=item["market_card_id"],
        source_player_id=None,
        effect_type="deal_damage",
        amount=item["amount"],
        target_player_ids=targets,
        selector=selector,
        is_attack=True,
        group=len(targets) > 1,
        source_kind=SourceKind.MARKET_MAYHEM,
        source_card_instance_id=item["market_instance_id"],
        defense_allowed=True,
        redirectable=False,
        metadata={"continue_market_attack_queue": True},
    )
    if needs_target_choice(state, state.current_player.id, selector) and len(targets) > 1:
        state.phase = GamePhase.CHOOSE_TARGET
        state.pending_choice = PendingChoice(
            choice_type=PendingChoiceType.CHOOSE_MARKET_ATTACK_TARGET,
            actor_id=state.current_player.id,
            choice_id=f"choice_{len(state.event_log)}_market_attack_target",
            source_card_id=item["market_card_id"],
            source_card_instance_id=item["market_instance_id"],
            source_kind=SourceKind.MARKET_MAYHEM,
            effect=request,
            options=[
                {
                    "id": f"target_{target_id}",
                    "target_player": target_id,
                    "description": f"Choose Player {target_id + 1} for market attack",
                }
                for target_id in targets
            ],
            metadata={"continue_market_attack_queue": True},
        )
        state.event_log.append(
            f"pending_choice_created: {PendingChoiceType.CHOOSE_MARKET_ATTACK_TARGET.value} "
            f"options={len(targets)} source_kind={SourceKind.MARKET_MAYHEM.value}"
        )
        return
    resolve_damage_request(state, request, database=database, rng=rng)


def resolve_market_weak_wand_item(state: GameState, item: dict) -> None:
    for target_id in item["target_player_ids"]:
        if state.weak_wand_stack:
            state.players[target_id].discard.append(state.weak_wand_stack.pop())
    state.event_log.append(
        f"market_mayhem_attack_resolved: weak_wand from {item['market_card_id']} "
        f"source_kind={SourceKind.MARKET_MAYHEM.value}"
    )


def resolve_market_discard_item(state: GameState, database: CardDatabase, item: dict) -> None:
    player = state.players[item["target_player_id"]]
    if not player.hand:
        state.event_log.append(f"market_mayhem_discard: {player.name} no hand cards")
        return
    if len(player.hand) == 1:
        instance_id = player.hand.pop()
        player.discard.append(instance_id)
        state.event_log.append(f"market_mayhem_discard: {player.name} discards {instance_id}")
        return
    state.phase = GamePhase.CHOOSE_TARGET
    state.pending_choice = PendingChoice(
        choice_type=PendingChoiceType.DISCARD_CARD,
        actor_id=player.id,
        choice_id=f"choice_{len(state.event_log)}_market_discard",
        source_card_id=item["market_card_id"],
        source_card_instance_id=item["market_instance_id"],
        source_kind=SourceKind.MARKET_MAYHEM,
        options=[
            {
                "id": f"discard_{index}",
                "instance_id": instance_id,
                "card_id": card_id_for(state, instance_id),
                "zone": "hand",
                "description": f"Discard {card_def_for(state, database, instance_id).name}",
            }
            for index, instance_id in enumerate(player.hand)
        ],
        metadata={"continue_market_attack_queue": True},
    )
    state.event_log.append(
        f"pending_choice_created: {PendingChoiceType.DISCARD_CARD.value} "
        f"options={len(player.hand)} source_kind={SourceKind.MARKET_MAYHEM.value}"
    )
