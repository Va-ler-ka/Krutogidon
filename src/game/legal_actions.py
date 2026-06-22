from __future__ import annotations

from .enums import ActionType, GamePhase
from .instances import card_def_for
from .models import Action, CardDatabase, GameState
from .card_text import parse_card_text
from .targeting import needs_target_choice, parse_selector_from_text, target_candidates


class LegalActionGenerator:
    def __init__(self, database: CardDatabase):
        self.database = database

    def generate(self, state: GameState) -> list[Action]:
        if state.game_over or state.phase == GamePhase.GAME_OVER:
            return []
        if state.phase == GamePhase.DEFENSE_WINDOW:
            return self._defense_actions(state)
        if state.phase == GamePhase.CHOOSE_TARGET:
            return self._target_actions(state)
        if state.phase in {GamePhase.START_OF_TURN, GamePhase.RESOLVING_EFFECT, GamePhase.END_OF_TURN, GamePhase.LEGEND_REVEAL}:
            return [Action(ActionType.NOOP, actor_id=state.current_player.id, description="Continue automatic phase")]
        return self._main_actions(state)

    def _main_actions(self, state: GameState) -> list[Action]:
        player = state.current_player
        actions: list[Action] = []

        for instance_id in player.hand:
            card = card_def_for(state, self.database, instance_id)
            attack_text = parse_card_text(card.text).attack_text or ""
            selector = parse_selector_from_text(attack_text)
            candidates = target_candidates(state, player.id, selector)
            if card.attack and needs_target_choice(state, player.id, selector) and len(candidates) > 1:
                actions.append(
                    Action(
                        ActionType.PLAY_CARD,
                        card_id=card.id,
                        instance_id=instance_id,
                        actor_id=player.id,
                        payload={"requires_target": True, "target_candidates": candidates},
                        description=f"Play {card.name} and choose target",
                    )
                )
            else:
                target = candidates[0] if card.attack and needs_target_choice(state, player.id, selector) and candidates else None
                actions.append(
                    Action(
                        ActionType.PLAY_CARD,
                        card_id=card.id,
                        instance_id=instance_id,
                        target_player=target,
                        actor_id=player.id,
                        payload={"target_candidates": candidates} if card.attack else {},
                        description=f"Play {card.name}",
                    )
                )

        for index, instance_id in enumerate(state.market):
            card = card_def_for(state, self.database, instance_id)
            if card.cost is not None and card.cost <= player.power:
                actions.append(
                    Action(
                        ActionType.BUY_MARKET_CARD,
                        card_id=card.id,
                        instance_id=instance_id,
                        market_index=index,
                        actor_id=player.id,
                        description=f"Buy market card {card.name}",
                    )
                )

        if state.current_legend and not player.has_defeated_legend_this_turn:
            legend = card_def_for(state, self.database, state.current_legend)
            if legend.cost is not None and legend.cost <= player.power:
                actions.append(
                    Action(
                        ActionType.DEFEAT_LEGEND,
                        card_id=legend.id,
                        instance_id=state.current_legend,
                        actor_id=player.id,
                        description=f"Defeat legend {legend.name}",
                    )
                )

        if state.wild_magic_stack:
            wild_magic = card_def_for(state, self.database, state.wild_magic_stack[-1])
            if wild_magic.cost is not None and wild_magic.cost <= player.power:
                actions.append(
                    Action(
                        ActionType.BUY_WILD_MAGIC,
                        card_id=wild_magic.id,
                        instance_id=state.wild_magic_stack[-1],
                        actor_id=player.id,
                        description=f"Buy {wild_magic.name}",
                    )
                )

        if not player.familiar_purchased and player.unbought_familiar_id:
            familiar = self.database.cards[player.unbought_familiar_id]
            if familiar.cost is not None and familiar.cost <= player.power:
                actions.append(
                    Action(
                        ActionType.BUY_FAMILIAR,
                        card_id=familiar.id,
                        instance_id=None,
                        actor_id=player.id,
                        description=f"Buy familiar {familiar.name}",
                    )
                )

        actions.append(Action(ActionType.END_TURN, actor_id=player.id, description="End turn"))
        return actions

    def _target_actions(self, state: GameState) -> list[Action]:
        choice = state.pending_choice
        if choice is None:
            return []
        return [
            Action(
                ActionType.CHOOSE_TARGET,
                actor_id=choice.actor_id,
                target_player=target_id,
                payload={"choice_type": choice.choice_type},
                description=f"Choose target Player {target_id + 1}",
            )
            for target_id in choice.candidates
        ]

    def _defense_actions(self, state: GameState) -> list[Action]:
        choice = state.pending_choice
        if choice is None or choice.effect is None:
            return []
        defender = state.players[choice.actor_id]
        actions: list[Action] = []
        for instance_id in defender.hand:
            card = card_def_for(state, self.database, instance_id)
            if card.defense:
                actions.append(
                    Action(
                        ActionType.USE_DEFENSE,
                        card_id=card.id,
                        instance_id=instance_id,
                        actor_id=defender.id,
                        payload={"defense_source": "hand"},
                        description=f"Use defense {card.name}",
                    )
                )
        actions.append(
            Action(
                ActionType.DECLINE_DEFENSE,
                actor_id=defender.id,
                description="Decline defense",
            )
        )
        return actions
