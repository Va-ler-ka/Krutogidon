from __future__ import annotations

import random
import re

from .card_text import parse_card_text
from .effects import apply_card_effect, decline_defense, use_defense_card
from .enums import ActionType, GamePhase
from .instances import card_def_for, card_id_for, create_card_instance, find_instance_for_card, set_owner
from .legal_actions import LegalActionGenerator
from .models import Action, CardDatabase, EffectRequest, GameState, PendingChoice, PlayerState
from .scoring import compute_winners
from .setup import draw_cards, fill_market
from .targeting import CHOSEN_ENEMY, needs_target_choice, parse_selector_from_text, target_candidates
from .triggers import fire_trigger


class GameEngine:
    def __init__(self, state: GameState, database: CardDatabase):
        self.state = state
        self.database = database
        self.rng = random.Random(state.config.seed)
        self.action_generator = LegalActionGenerator(database)

    def legal_actions(self) -> list[Action]:
        return self.action_generator.generate(self.state)

    def step(self, action: Action) -> None:
        if self.state.game_over:
            return
        if not self._is_action_legal(action):
            raise ValueError(f"Illegal action in phase {self.state.phase}: {action}")

        if action.type == ActionType.NOOP:
            self._continue_automatic_phase()
        elif action.type == ActionType.PLAY_CARD:
            self.play_card(action)
        elif action.type == ActionType.BUY_MARKET_CARD:
            self.buy_market_card(action)
        elif action.type == ActionType.DEFEAT_LEGEND:
            self.defeat_legend()
        elif action.type == ActionType.BUY_WILD_MAGIC:
            self.buy_wild_magic()
        elif action.type == ActionType.BUY_FAMILIAR:
            self.buy_familiar()
        elif action.type == ActionType.CHOOSE_TARGET:
            self.choose_target(action)
        elif action.type == ActionType.USE_DEFENSE:
            self.use_defense(action)
        elif action.type == ActionType.DECLINE_DEFENSE:
            self.decline_defense(action)
        elif action.type == ActionType.END_TURN:
            self.end_turn()
        else:
            raise ValueError(f"Unsupported action: {action.type}")
        self.check_game_over()

    def play_card(self, action: Action) -> None:
        player = self.state.current_player
        instance_id = action.instance_id or find_instance_for_card(self.state, player.hand, action.card_id or "")
        if instance_id not in player.hand:
            raise ValueError(f"Card is not in hand: {action.card_id or action.instance_id}")
        player.hand.remove(instance_id)
        card = card_def_for(self.state, self.database, instance_id)
        if card.ongoing:
            player.ongoing.append(instance_id)
            fire_trigger(self.state, self.database, "on_card_played", player.id, instance_id)
        else:
            player.played.append(instance_id)
        self.state.event_log.append(f"{player.name} играет {card.name}")

        attack_text = parse_card_text(card.text).attack_text or ""
        attack_selector = parse_selector_from_text(attack_text)
        if card.attack and action.target_player is None and needs_target_choice(self.state, player.id, attack_selector):
            apply_card_effect(
                state=self.state,
                player=player,
                card=card,
                rng=self.rng,
                strict=self.state.config.strict,
                database=self.database,
                include_attack=False,
            )
            self.state.phase = GamePhase.CHOOSE_TARGET
            self.state.pending_choice = PendingChoice(
                choice_type="attack_target",
                    actor_id=player.id,
                    source_player_id=player.id,
                    source_card_id=card.id,
                candidates=target_candidates(self.state, player.id, attack_selector),
                effect=EffectRequest(
                    source_card_id=card.id,
                    source_player_id=player.id,
                    effect_type="card_attack",
                    amount=extract_damage_amount(card.text),
                    selector=attack_selector,
                    is_attack=True,
                ),
                prompt=f"Choose target for {card.name}",
            )
            return

        apply_card_effect(
            state=self.state,
            player=player,
            card=card,
            rng=self.rng,
            strict=self.state.config.strict,
            target_player=action.target_player,
            database=self.database,
        )
        if self.state.phase != GamePhase.DEFENSE_WINDOW:
            self.state.phase = GamePhase.MAIN

    def choose_target(self, action: Action) -> None:
        choice = self.state.pending_choice
        if choice is None or choice.effect is None:
            raise ValueError("No target choice is pending")
        if action.target_player not in choice.candidates:
            raise ValueError("Target is not a legal candidate")
        player = self.state.players[choice.source_player_id if choice.source_player_id is not None else choice.actor_id]
        card = self.database.cards[choice.source_card_id] if choice.source_card_id else None
        choice.effect.target_player_ids = [action.target_player]
        self.state.pending_choice = None
        self.state.phase = GamePhase.RESOLVING_EFFECT
        if card is not None:
            apply_card_effect(
                state=self.state,
                player=player,
                card=card,
                rng=self.rng,
                strict=self.state.config.strict,
                target_player=action.target_player,
                database=self.database,
                include_attack=True,
            )
        if self.state.phase != GamePhase.DEFENSE_WINDOW:
            self.state.phase = GamePhase.MAIN

    def use_defense(self, action: Action) -> None:
        source = action.payload.get("defense_source", "hand")
        use_defense_card(
            state=self.state,
            database=self.database,
            defender_id=action.actor_id if action.actor_id is not None else self.state.pending_choice.actor_id,
            defense_card_id=action.instance_id or action.card_id or "",
            rng=self.rng,
            source=source,
        )

    def decline_defense(self, action: Action) -> None:
        defender_id = action.actor_id if action.actor_id is not None else self.state.pending_choice.actor_id
        decline_defense(state=self.state, database=self.database, defender_id=defender_id, rng=self.rng)

    def buy_market_card(self, action: Action) -> None:
        player = self.state.current_player
        if action.market_index is None or action.market_index >= len(self.state.market):
            raise ValueError("Invalid market index")
        instance_id = self.state.market[action.market_index]
        card = card_def_for(self.state, self.database, instance_id)
        if action.instance_id and action.instance_id != instance_id:
            raise ValueError("Action instance_id does not match market slot")
        if action.card_id and action.card_id not in {card.id, instance_id}:
            raise ValueError("Action card_id does not match market slot")
        if card.cost is None or card.cost > player.power:
            raise ValueError("Not enough power")
        player.power -= card.cost
        set_owner(self.state, instance_id, player.id)
        if player.next_gained_card_to_top_deck:
            player.deck.append(instance_id)
            player.next_gained_card_to_top_deck = False
        else:
            player.discard.append(instance_id)
        del self.state.market[action.market_index]
        self.state.event_log.append(f"{player.name} покупает {card.name}")
        fire_trigger(self.state, self.database, "on_card_bought", player.id, instance_id)
        fill_market(self.state, self.database, self.rng)
        self.state.phase = GamePhase.MAIN

    def defeat_legend(self) -> None:
        player = self.state.current_player
        if not self.state.current_legend:
            raise ValueError("No current legend")
        if player.has_defeated_legend_this_turn:
            raise ValueError("Only one legend can be defeated per turn")
        legend_instance = self.state.current_legend
        legend = card_def_for(self.state, self.database, legend_instance)
        if legend.cost is None or legend.cost > player.power:
            raise ValueError("Not enough power for legend")
        player.power -= legend.cost
        set_owner(self.state, legend_instance, player.id)
        player.discard.append(legend_instance)
        player.defeated_legends += 1
        player.has_defeated_legend_this_turn = True
        self.state.event_log.append(f"{player.name} побеждает легенду {legend.name}")
        self.state.current_legend = None
        self.state.phase = GamePhase.MAIN

    def buy_wild_magic(self) -> None:
        player = self.state.current_player
        if not self.state.wild_magic_stack:
            raise ValueError("Wild magic stack is empty")
        instance_id = self.state.wild_magic_stack[-1]
        card = card_def_for(self.state, self.database, instance_id)
        if card.cost is None or card.cost > player.power:
            raise ValueError("Not enough power")
        player.power -= card.cost
        bought = self.state.wild_magic_stack.pop()
        set_owner(self.state, bought, player.id)
        player.discard.append(bought)
        self.state.event_log.append(f"{player.name} покупает {card.name}")
        self.state.phase = GamePhase.MAIN

    def buy_familiar(self) -> None:
        player = self.state.current_player
        if player.familiar_purchased:
            raise ValueError("Player already has a familiar")
        if not player.unbought_familiar_id:
            raise ValueError("Player has no assigned familiar")
        card_id = player.unbought_familiar_id
        card = self.database.cards[card_id]
        if card.cost is None or card.cost > player.power:
            raise ValueError("Not enough power")
        player.power -= card.cost
        instance_id = create_card_instance(self.state, card_id, owner_id=player.id, origin="familiar")
        player.discard.append(instance_id)
        player.familiar_purchased = True
        self.state.event_log.append(f"{player.name} покупает фамильяра {card.name}")
        self.state.phase = GamePhase.MAIN

    def end_turn(self) -> None:
        self.state.phase = GamePhase.END_OF_TURN
        player = self.state.current_player
        fire_trigger(self.state, self.database, "on_end_turn", player.id)
        player.discard.extend(player.hand)
        player.hand = []
        player.discard.extend(player.played)
        player.played = []
        player.power = 0
        player.has_defeated_legend_this_turn = False
        draw_cards(self.state, player, self.state.config.hand_size, self.rng)

        if self.state.current_legend is None and self.state.legend_deck:
            self.state.phase = GamePhase.LEGEND_REVEAL
            self.state.current_legend = self.state.legend_deck.pop(0)
            legend = card_def_for(self.state, self.database, self.state.current_legend)
            self.state.event_log.append(f"Раскрыта новая легенда: {legend.name}")
            if legend.group_attack:
                self.resolve_group_attack(legend.id)
        elif self.state.current_legend is None and not self.state.legend_deck:
            self.state.game_over = True
            self.state.end_reason = "legend_deck_empty"
            self.state.phase = GamePhase.GAME_OVER
            return

        self.state.current_player_index = (self.state.current_player_index + 1) % len(self.state.players)
        self.state.turn_number += 1
        self.state.phase = GamePhase.START_OF_TURN
        fire_trigger(self.state, self.database, "on_start_turn", self.state.current_player.id)
        self.state.phase = GamePhase.MAIN
        if self.state.turn_number > self.state.config.max_turns:
            self.state.game_over = True
            self.state.end_reason = "max_turns"
            self.state.phase = GamePhase.GAME_OVER

    def resolve_group_attack(self, legend_id: str) -> None:
        legend = card_def_for(self.state, self.database, legend_id)
        group_text = parse_card_text(legend.text).group_attack_text or ""
        damage = extract_damage_amount(group_text)
        self.state.event_log.append(f"Групповая атака легенды: {legend.name}")
        if damage <= 0:
            if self.state.config.strict:
                raise NotImplementedError(f"Group attack not implemented for {legend.id}: {legend.text}")
            self.state.event_log.append(f"{legend.name}: group attack not_implemented")
            return
        actor_id = self.state.current_player.id
        targets = group_attack_order(self.state)
        request = EffectRequest(
            source_card_id=legend.id,
            source_player_id=actor_id,
            effect_type="deal_damage",
            amount=damage,
            target_player_ids=targets,
            is_attack=True,
            group=True,
        )
        self.state.effect_queue.append(request)
        from .effects import resolve_damage_request

        resolve_damage_request(self.state, request, database=self.database, rng=self.rng)

    def check_game_over(self) -> None:
        if not self.state.game_over:
            if len(self.state.market) < self.state.config.market_size and not self.state.main_deck:
                self.state.game_over = True
                self.state.end_reason = "main_deck_empty"
            if not self.state.dead_wizard_stack and any(player.health <= 0 for player in self.state.players):
                self.state.game_over = True
                self.state.end_reason = "dead_wizard_tokens_empty"
        if self.state.game_over:
            self.state.phase = GamePhase.GAME_OVER
        if self.state.game_over and not self.state.winner_ids:
            self.state.winner_ids = compute_winners(self.state, self.database)

    def _continue_automatic_phase(self) -> None:
        if self.state.phase != GamePhase.GAME_OVER:
            self.state.phase = GamePhase.MAIN

    def _is_action_legal(self, action: Action) -> bool:
        legal_actions = self.legal_actions()
        if not legal_actions:
            return False
        return any(actions_match(action, legal) for legal in legal_actions)


def actions_match(actual: Action, legal: Action) -> bool:
    if actual.type != legal.type:
        return False
    if actual.actor_id is not None and legal.actor_id is not None and actual.actor_id != legal.actor_id:
        return False
    if actual.instance_id is not None and actual.instance_id != legal.instance_id:
        return False
    if actual.card_id is not None and actual.card_id not in {legal.card_id, legal.instance_id}:
        return False
    if actual.market_index is not None and actual.market_index != legal.market_index:
        return False
    target_candidates = legal.payload.get("target_candidates", [])
    if actual.target_player is not None and target_candidates and actual.target_player in target_candidates:
        return True
    if actual.target_player is not None and actual.target_player != legal.target_player:
        return False
    return True


def extract_damage_amount(text: str) -> int:
    match = re.search(r"нанеси\s+(\d+)\s+урон\w*", text.lower())
    return int(match.group(1)) if match else 0


def group_attack_order(state: GameState) -> list[int]:
    if not state.players:
        return []
    start = (state.current_player_index + 1) % len(state.players)
    return [(start + offset) % len(state.players) for offset in range(len(state.players))]


def choose_default_target(state: GameState, player: PlayerState) -> int | None:
    opponents = [candidate for candidate in state.players if candidate.id != player.id]
    if not opponents:
        return None
    return min(opponents, key=lambda candidate: candidate.health).id
