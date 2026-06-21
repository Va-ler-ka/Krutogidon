from __future__ import annotations

import random

from src.game.enums import ActionType
from src.game.models import Action, CardDatabase, GameState


class RandomAgent:
    def __init__(self, seed: int | None = None):
        self.rng = random.Random(seed)

    def choose_action(
        self,
        observation: GameState,
        legal_actions: list[Action],
        database: CardDatabase,
    ) -> Action:
        if not legal_actions:
            raise ValueError("RandomAgent received no legal actions")

        target_or_defense = [
            action
            for action in legal_actions
            if action.type in {ActionType.CHOOSE_TARGET, ActionType.USE_DEFENSE, ActionType.DECLINE_DEFENSE}
        ]
        if target_or_defense:
            defenses = [action for action in target_or_defense if action.type == ActionType.USE_DEFENSE]
            if defenses and self.rng.random() < 0.35:
                return self.rng.choice(defenses)
            declines = [action for action in target_or_defense if action.type == ActionType.DECLINE_DEFENSE]
            if declines:
                return self.rng.choice(declines)
            return self.rng.choice(target_or_defense)

        playable = [action for action in legal_actions if action.type == ActionType.PLAY_CARD]
        if playable:
            return self.rng.choice(playable)

        affordable = [
            action
            for action in legal_actions
            if action.type
            in {
                ActionType.BUY_MARKET_CARD,
                ActionType.DEFEAT_LEGEND,
                ActionType.BUY_WILD_MAGIC,
                ActionType.BUY_FAMILIAR,
            }
        ]
        if affordable and self.rng.random() < 0.75:
            return self.rng.choice(affordable)

        return next(action for action in legal_actions if action.type == ActionType.END_TURN)
