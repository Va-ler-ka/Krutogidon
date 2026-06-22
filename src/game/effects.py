from __future__ import annotations

import random
import re
from dataclasses import dataclass
from typing import Protocol

from .enums import GamePhase
from .card_text import parse_card_text
from .instances import card_def_for, card_id_for
from .models import CardDefinition, EffectRequest, GameState, PendingChoice, PlayerState
from .setup import draw_cards
from .targeting import CHOSEN_ENEMY, target_candidates


TODO_RULE_CLARIFICATION_DEATH_RESET_HEALTH = (
    "TODO_RULE_CLARIFICATION: exact health reset after receiving a dead wizard token must be checked."
)


@dataclass
class EffectResult:
    implemented: bool
    notes: str = ""


class EffectPrimitive(Protocol):
    def apply(
        self,
        *,
        state: GameState,
        player: PlayerState,
        card: CardDefinition | None,
        rng: random.Random,
        database=None,
    ) -> EffectResult:
        ...


@dataclass(frozen=True)
class GainPower:
    amount: int

    def apply(self, *, state: GameState, player: PlayerState, card: CardDefinition | None, rng: random.Random, database=None) -> EffectResult:
        player.power += self.amount
        return EffectResult(True)


@dataclass(frozen=True)
class DrawCards:
    count: int

    def apply(self, *, state: GameState, player: PlayerState, card: CardDefinition | None, rng: random.Random, database=None) -> EffectResult:
        draw_cards(state, player, self.count, rng)
        return EffectResult(True)


@dataclass(frozen=True)
class Heal:
    amount: int

    def apply(self, *, state: GameState, player: PlayerState, card: CardDefinition | None, rng: random.Random, database=None) -> EffectResult:
        player.health += self.amount
        return EffectResult(True)


@dataclass(frozen=True)
class DealDamage:
    selector: str
    amount: int
    is_attack: bool = True
    target_player: int | None = None

    def apply(self, *, state: GameState, player: PlayerState, card: CardDefinition | None, rng: random.Random, database=None) -> EffectResult:
        targets = [self.target_player] if self.target_player is not None else target_candidates(state, player.id, self.selector)
        targets = [target for target in targets if target is not None and target != player.id]
        if not targets:
            return EffectResult(False, "no legal damage target")
        request = EffectRequest(
            source_card_id=card.id if card else "",
            source_player_id=player.id,
            effect_type="deal_damage",
            amount=self.amount,
            target_player_ids=targets,
            selector=self.selector,
            is_attack=self.is_attack,
            group=len(targets) > 1,
        )
        resolve_damage_request(state, request, database=database, rng=rng)
        return EffectResult(True)


@dataclass(frozen=True)
class DiscardCards:
    selector: str
    count: int

    def apply(self, *, state: GameState, player: PlayerState, card: CardDefinition | None, rng: random.Random, database=None) -> EffectResult:
        targets = target_candidates(state, player.id, self.selector)
        for target_id in targets:
            target = state.players[target_id]
            for _ in range(min(self.count, len(target.hand))):
                target.discard.append(target.hand.pop())
        return EffectResult(True)


@dataclass(frozen=True)
class DestroyCard:
    zone_selector: str

    def apply(self, *, state: GameState, player: PlayerState, card: CardDefinition | None, rng: random.Random, database=None) -> EffectResult:
        if self.zone_selector == "hand" and player.hand:
            player.destroyed.append(player.hand.pop())
            return EffectResult(True)
        if self.zone_selector == "discard" and player.discard:
            player.destroyed.append(player.discard.pop())
            return EffectResult(True)
        if self.zone_selector == "hand_or_discard":
            if player.hand:
                player.destroyed.append(player.hand.pop())
                return EffectResult(True)
            if player.discard:
                player.destroyed.append(player.discard.pop())
                return EffectResult(True)
        state.event_log.append(f"DestroyCard({self.zone_selector}) not_implemented")
        return EffectResult(False, "destroy card target unavailable")


@dataclass(frozen=True)
class GainCard:
    source_selector: str

    def apply(self, *, state: GameState, player: PlayerState, card: CardDefinition | None, rng: random.Random, database=None) -> EffectResult:
        if self.source_selector == "market" and state.market:
            instance_id = state.market.pop(0)
            if player.next_gained_card_to_top_deck:
                player.deck.append(instance_id)
                player.next_gained_card_to_top_deck = False
            else:
                player.discard.append(instance_id)
            return EffectResult(True)
        state.event_log.append(f"GainCard({self.source_selector}) not_implemented")
        return EffectResult(False, "gain card not implemented")


@dataclass(frozen=True)
class GiveWeakWand:
    selector: str
    count: int

    def apply(self, *, state: GameState, player: PlayerState, card: CardDefinition | None, rng: random.Random, database=None) -> EffectResult:
        if database is None or not database.weak_wand_id:
            return EffectResult(False, "weak wand stack unavailable")
        for target_id in target_candidates(state, player.id, self.selector):
            target = state.players[target_id]
            for _ in range(self.count):
                if not state.weak_wand_stack:
                    break
                target.discard.append(state.weak_wand_stack.pop())
        return EffectResult(True)


@dataclass(frozen=True)
class RevealHand:
    selector: str

    def apply(self, *, state: GameState, player: PlayerState, card: CardDefinition | None, rng: random.Random, database=None) -> EffectResult:
        for target_id in target_candidates(state, player.id, self.selector):
            state.event_log.append(f"{state.players[target_id].name} reveals hand: {state.players[target_id].hand}")
        return EffectResult(True)


@dataclass(frozen=True)
class ConditionalEffect:
    condition: str
    then_effect: EffectPrimitive
    else_effect: EffectPrimitive | None = None

    def apply(self, *, state: GameState, player: PlayerState, card: CardDefinition | None, rng: random.Random, database=None) -> EffectResult:
        state.event_log.append(f"ConditionalEffect({self.condition}) not_implemented; applying else branch if present")
        if self.else_effect:
            return self.else_effect.apply(state=state, player=player, card=card, rng=rng, database=database)
        return EffectResult(False, "condition not implemented")


@dataclass(frozen=True)
class CompositeEffect:
    effects: list[EffectPrimitive]

    def apply(self, *, state: GameState, player: PlayerState, card: CardDefinition | None, rng: random.Random, database=None) -> EffectResult:
        implemented = False
        notes: list[str] = []
        for effect in self.effects:
            result = effect.apply(state=state, player=player, card=card, rng=rng, database=database)
            implemented = implemented or result.implemented
            if result.notes:
                notes.append(result.notes)
        return EffectResult(implemented, "; ".join(notes))


effect_registry: dict[str, type[EffectPrimitive] | EffectPrimitive] = {
    "gain_power": GainPower,
    "draw_cards": DrawCards,
    "heal": Heal,
    "deal_damage": DealDamage,
    "discard_cards": DiscardCards,
    "destroy_card": DestroyCard,
    "gain_card": GainCard,
    "give_weak_wand": GiveWeakWand,
    "reveal_hand": RevealHand,
    "conditional": ConditionalEffect,
    "composite": CompositeEffect,
}


def apply_card_effect(
    *,
    state: GameState,
    player: PlayerState,
    card: CardDefinition,
    rng: random.Random,
    strict: bool,
    target_player: int | None = None,
    database=None,
    include_attack: bool = True,
) -> None:
    effect = parse_basic_effect(card, target_player=target_player, include_attack=include_attack, mode="play")
    result = effect.apply(state=state, player=player, card=card, rng=rng, database=database)
    if strict and card.text and card.text != "(Эффекта нет.)" and (not result.implemented or has_unparsed_complex_text(card)):
        raise NotImplementedError(f"Effect not implemented for {card.id}: {card.text}")
    if result.notes:
        state.event_log.append(f"{card.name}: {result.notes}")
    if result.implemented and has_unparsed_complex_text(card):
        state.event_log.append(f"{card.name}: basic parts applied; complex text skipped")
    elif not result.implemented and card.text and card.text != "(Эффекта нет.)":
        state.event_log.append(f"{card.name}: effect skipped ({card.implementation_status})")


def parse_basic_effect(
    card: CardDefinition,
    *,
    target_player: int | None = None,
    include_attack: bool = True,
    mode: str = "play",
) -> CompositeEffect:
    sections = parse_card_text(card.text)
    if mode == "defense":
        source_text = sections.defense_text or ""
    elif mode == "group_attack":
        source_text = sections.group_attack_text or ""
    elif mode == "attack":
        source_text = sections.attack_text or ""
    else:
        parts = [sections.main_text]
        if include_attack and sections.attack_text:
            parts.append(sections.attack_text)
        source_text = " ".join(part for part in parts if part)
    text = source_text.lower()
    effects: list[EffectPrimitive] = []
    if mode == "play" and card.power and (sections.main_text or not sections.attack_text):
        effects.append(GainPower(card.power))

    draw_match = re.search(r"возьми\s+(\d+)\s+карт", text)
    if draw_match:
        effects.append(DrawCards(int(draw_match.group(1))))

    heal_match = re.search(r"накрути\s+(\d+)\s+жизн", text)
    if heal_match:
        effects.append(Heal(int(heal_match.group(1))))

    if include_attack and mode in {"play", "attack", "group_attack"}:
        damage_match = re.search(r"нанеси\s+(\d+)\s+урон", text)
        if damage_match:
            selector = "all_enemies" if "кажд" in text else CHOSEN_ENEMY
            effects.append(
                DealDamage(
                    selector,
                    int(damage_match.group(1)),
                    is_attack=card.attack,
                    target_player=target_player,
                )
            )

    return CompositeEffect(effects)


def resolve_damage_request(state: GameState, request: EffectRequest, *, database, rng: random.Random) -> None:
    while request.current_target_index < len(request.target_player_ids):
        target_id = request.target_player_ids[request.current_target_index]
        if request.is_attack and database is not None and has_available_defense(state, database, target_id):
            state.phase = GamePhase.DEFENSE_WINDOW
            state.pending_choice = PendingChoice(
                choice_type="defense",
                actor_id=target_id,
                source_player_id=request.source_player_id,
                source_card_id=request.source_card_id,
                effect=request,
                prompt=f"{state.players[target_id].name} may defend against attack",
            )
            return
        apply_damage(state, request.source_player_id, target_id, request.amount)
        request.current_target_index += 1
    state.pending_choice = None
    state.phase = GamePhase.MAIN


def has_available_defense(state: GameState, database, player_id: int) -> bool:
    player = state.players[player_id]
    if any(card_def_for(state, database, instance_id).defense for instance_id in player.hand):
        return True
    return False


def use_defense_card(
    *,
    state: GameState,
    database,
    defender_id: int,
    defense_card_id: str,
    rng: random.Random,
    source: str = "hand",
) -> None:
    choice = state.pending_choice
    if choice is None or choice.effect is None:
        raise ValueError("No defense window is open")
    if choice.actor_id != defender_id:
        raise ValueError("Defense action actor does not match pending defender")
    defender = state.players[defender_id]
    defense_ref = defense_card_id
    if source == "hand":
        if defense_ref not in defender.hand:
            raise ValueError("Defense card is not in hand")
        defender.hand.remove(defense_ref)
        defender.discard.append(defense_ref)
    else:
        raise ValueError(f"Unsupported defense source: {source}")

    card = card_def_for(state, database, defense_ref)
    defense_effect = parse_basic_effect(card, include_attack=False, mode="defense")
    defense_effect.apply(state=state, player=defender, card=card, rng=rng, database=database)
    state.event_log.append(f"{defender.name} uses defense {card.name}")

    request = choice.effect
    if "перенаправ" in (parse_card_text(card.text).defense_text or "").lower():
        apply_damage(state, defender_id, request.source_player_id, request.amount)
        state.event_log.append(f"{card.name}: redirected attack to {state.players[request.source_player_id].name}")
    request.current_target_index += 1
    resolve_damage_request(state, request, database=database, rng=rng)


def decline_defense(*, state: GameState, database, defender_id: int, rng: random.Random) -> None:
    choice = state.pending_choice
    if choice is None or choice.effect is None:
        raise ValueError("No defense window is open")
    if choice.actor_id != defender_id:
        raise ValueError("Defense action actor does not match pending defender")
    request = choice.effect
    target_id = request.target_player_ids[request.current_target_index]
    apply_damage(state, request.source_player_id, target_id, request.amount)
    request.current_target_index += 1
    resolve_damage_request(state, request, database=database, rng=rng)


def apply_damage(state: GameState, source_player_id: int, target_player_id: int, amount: int) -> None:
    target = state.players[target_player_id]
    target.health -= amount
    state.event_log.append(
        f"{state.players[source_player_id].name} deals {amount} damage to {target.name}"
    )
    if target.health <= 0:
        handle_player_death(state, target)


def handle_player_death(state: GameState, player: PlayerState) -> None:
    if state.dead_wizard_stack:
        token_id = state.dead_wizard_stack.pop()
        player.dead_wizard_tokens.append(token_id)
        player.health = state.config.death_reset_health
        state.event_log.append(
            f"{player.name} receives dead wizard token {token_id}; {TODO_RULE_CLARIFICATION_DEATH_RESET_HEALTH}"
        )
    else:
        state.game_over = True
        state.end_reason = "dead_wizard_tokens_empty"
        state.phase = GamePhase.GAME_OVER


def has_unparsed_complex_text(card: CardDefinition) -> bool:
    lower = card.text.lower()
    simple_patterns = [
        r"\+\d+\s*мощ\w*",
        r"возьми\s+\d+\s+карт",
        r"нанеси\s+\d+\s+урон",
        r"накрути\s+\d+\s+жизн",
        r"атака:",
        r"защита:",
    ]
    stripped = lower
    for pattern in simple_patterns:
        stripped = re.sub(pattern, "", stripped)
    stripped = stripped.replace(".", "").replace("и", "").strip()
    return bool(stripped and stripped != "(эффекта нет)")
