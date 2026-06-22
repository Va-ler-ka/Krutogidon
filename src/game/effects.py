from __future__ import annotations

import random
import re
from dataclasses import dataclass
from typing import Protocol

from .enums import GamePhase
from .card_text import parse_card_text
from .instances import card_def_for, card_id_for
from .models import CardDefinition, EffectRequest, GameState, PendingChoice, PlayerState, SourceKind
from .setup import draw_cards
from .targeting import ALL_ENEMIES, CHOSEN_ENEMY, parse_selector_from_text, target_candidates


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
        player.health = min(state.config.max_health, player.health + self.amount)
        return EffectResult(True)


@dataclass(frozen=True)
class DealDamage:
    selector: str
    amount: int
    is_attack: bool = True
    target_player: int | None = None
    draw_on_kill_cards: int = 0

    def apply(self, *, state: GameState, player: PlayerState, card: CardDefinition | None, rng: random.Random, database=None) -> EffectResult:
        targets = [self.target_player] if self.target_player is not None else target_candidates(state, player.id, self.selector)
        if self.selector in {CHOSEN_ENEMY, ALL_ENEMIES}:
            targets = [target for target in targets if target is not None and target != player.id]
        else:
            targets = [target for target in targets if target is not None]
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
            source_kind=SourceKind.PLAYER_CARD,
            defense_allowed=self.is_attack,
            redirectable=self.is_attack,
            metadata={"draw_on_kill_cards": self.draw_on_kill_cards},
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
    kill_draw_pattern = r"если .*?подох.*?возьми\s+(\d+)\s+карт\w*"
    text_without_attack_conditions = re.sub(kill_draw_pattern, "", text)
    effects: list[EffectPrimitive] = []
    if mode == "play" and card.power and (sections.main_text or not sections.attack_text):
        effects.append(GainPower(card.power))

    draw_match = re.search(r"возьми\s+(\d+)\s+карт\w*", text_without_attack_conditions)
    if draw_match:
        effects.append(DrawCards(int(draw_match.group(1))))

    heal_match = re.search(r"накрути\s+(\d+)\s+жизн", text_without_attack_conditions)
    if heal_match:
        effects.append(Heal(int(heal_match.group(1))))

    discard_match = re.search(r"сбрасывает\s+(\d+)\s+карт\w*", text_without_attack_conditions)
    if discard_match:
        effects.append(DiscardCards(parse_selector_from_text(text), int(discard_match.group(1))))

    if include_attack and mode in {"play", "attack", "group_attack"}:
        damage_match = re.search(r"нанеси\s+(\d+)\s+урон\w*", text)
        if not damage_match:
            damage_match = re.search(r"нанеси\s+(?:выбранному\s+(?:врагу|колдуну)\s+)?(\d+)\s+урон\w*", text)
        if damage_match:
            selector = parse_selector_from_text(text)
            draw_on_kill = 0
            kill_draw_match = re.search(kill_draw_pattern, text)
            if kill_draw_match:
                draw_on_kill = int(kill_draw_match.group(1))
            effects.append(
                DealDamage(
                    selector,
                    int(damage_match.group(1)),
                    is_attack=card.attack,
                    target_player=target_player,
                    draw_on_kill_cards=draw_on_kill,
                )
            )

    if "получает вялую палочку" in text or "получают вялую палочку" in text:
        effects.append(GiveWeakWand(parse_selector_from_text(text), 1))

    return CompositeEffect(effects)


def resolve_damage_request(state: GameState, request: EffectRequest, *, database, rng: random.Random) -> None:
    while request.current_target_index < len(request.target_player_ids):
        target_id = request.target_player_ids[request.current_target_index]
        if request.is_attack and request.defense_allowed and database is not None and has_available_defense(state, database, target_id):
            state.phase = GamePhase.DEFENSE_WINDOW
            state.event_log.append(
                f"defense offered to {state.players[target_id].name} "
                f"(source_kind={request.source_kind.value}, redirectable={request.redirectable})"
            )
            state.pending_choice = PendingChoice(
                choice_type="defense",
                actor_id=target_id,
                source_player_id=request.source_player_id,
                source_card_id=request.source_card_id,
                effect=request,
                prompt=f"{state.players[target_id].name} may defend against attack",
            )
            return
        died = apply_damage(state, target_id, request.amount, request)
        draw_on_kill = int(request.metadata.get("draw_on_kill_cards", 0))
        if died and draw_on_kill and request.source_player_id is not None:
            draw_cards(state, state.players[request.source_player_id], draw_on_kill, rng)
            state.event_log.append(
                f"{state.players[request.source_player_id].name} draws {draw_on_kill} cards after kill"
            )
        request.current_target_index += 1
    state.pending_choice = None
    state.phase = GamePhase.MAIN
    if request.metadata.get("advance_turn_after_resolution"):
        state.pending_turn_advance = True


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
        if request.redirectable and request.source_player_id is not None and not request.already_redirected:
            redirect_request = EffectRequest(
                source_card_id=card.id,
                source_player_id=defender_id,
                effect_type="deal_damage",
                amount=request.amount,
                target_player_ids=[request.source_player_id],
                is_attack=False,
                source_kind=SourceKind.PLAYER_CARD,
                defense_allowed=False,
                redirectable=False,
                metadata={"redirected_from": request.source_kind},
            )
            request.already_redirected = True
            apply_damage(state, request.source_player_id, request.amount, redirect_request)
            state.event_log.append(f"{card.name}: redirected attack to {state.players[request.source_player_id].name}")
        else:
            state.event_log.append(f"{card.name}: redirect ignored (source not redirectable)")
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
    died = apply_damage(state, target_id, request.amount, request)
    draw_on_kill = int(request.metadata.get("draw_on_kill_cards", 0))
    if died and draw_on_kill and request.source_player_id is not None:
        draw_cards(state, state.players[request.source_player_id], draw_on_kill, rng)
    request.current_target_index += 1
    resolve_damage_request(state, request, database=database, rng=rng)


def apply_damage(state: GameState, target_player_id: int, amount: int, request: EffectRequest) -> bool:
    target = state.players[target_player_id]
    target.health -= amount
    state.event_log.append(
        f"{source_label(state, request)} deals {amount} damage to {target.name} "
        f"(source_kind={request.source_kind.value})"
    )
    if target.health <= 0:
        handle_player_death(state, target, request)
        return True
    return False


def handle_player_death(state: GameState, player: PlayerState, request: EffectRequest) -> None:
    maybe_award_trophy(state, player.id, request)
    if state.dead_wizard_stack:
        token_id = state.dead_wizard_stack.pop()
        player.dead_wizard_tokens.append(token_id)
        player.health = state.config.death_reset_health
        state.event_log.append(
            f"{player.name} dies and receives dead wizard token {token_id} "
            f"(source_kind={request.source_kind.value})"
        )
        state.event_log.append(f"{player.name} resets to {state.config.death_reset_health} health")
    else:
        state.game_over = True
        state.end_reason = "dead_wizard_tokens_empty"
        state.phase = GamePhase.GAME_OVER
        state.event_log.append(f"{player.name} dies; dead wizard token stack is empty")


def maybe_award_trophy(state: GameState, killed_player_id: int, request: EffectRequest) -> None:
    if request.source_kind not in {SourceKind.PLAYER_CARD, SourceKind.PLAYER_MAYHEM}:
        return
    if request.source_player_id is None or request.source_player_id == killed_player_id:
        return
    previous = state.trophy_controller_id
    state.trophy_controller_id = request.source_player_id
    state.event_log.append(
        f"trophy_change: player {request.source_player_id} gains Main Prize after killing player {killed_player_id}"
        f" (previous={previous}, source_kind={request.source_kind.value})"
    )


def source_label(state: GameState, request: EffectRequest) -> str:
    if request.source_player_id is not None:
        return state.players[request.source_player_id].name
    if request.source_kind == SourceKind.LEGEND_GROUP_ATTACK:
        return "Legend group attack"
    if request.source_kind == SourceKind.MARKET_MAYHEM:
        return "Market mayhem"
    if request.source_kind == SourceKind.PLAYER_MAYHEM:
        return "Player mayhem"
    return request.source_kind.value


def has_unparsed_complex_text(card: CardDefinition) -> bool:
    lower = card.text.lower()
    simple_patterns = [
        r"если .*?подох.*?возьми\s+\d+\s+карт\w*",
        r"каждому\s+врагу\s+хилее\s+тебя",
        r"правому\s+или\s+левому\s+врагу",
        r"левому\s+или\s+правому\s+врагу",
        r"(и\s+)?он\s+получает\s+вял\w+\s+палочк\w*",
        r"получа\w+\s+вял\w+\s+палочк\w*",
        r"сбрасывает\s+\d+\s+карт\w*",
        r"\+\d+\s*мощ\w*",
        r"возьми\s+\d+\s+карт\w*",
        r"нанеси\s+(?:выбранному\s+(?:врагу|колдуну)\s+)?\d+\s+урон\w*",
        r"нанеси\s+\d+\s+урон\w*",
        r"накрути\s+\d+\s+жизн",
        r"выбранному\s+(врагу|колдуну)",
        r"каждому\s+(врагу|колдуну)",
        r"атака:",
        r"защита:",
    ]
    stripped = lower
    for pattern in simple_patterns:
        stripped = re.sub(pattern, "", stripped)
    stripped = stripped.replace(".", "").replace("и", "").strip()
    return bool(stripped and stripped != "(эффекта нет)")
