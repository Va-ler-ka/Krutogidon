from __future__ import annotations

from typing import Protocol

from src.game.models import Action, CardDatabase, GameState


class Agent(Protocol):
    def choose_action(
        self,
        observation: GameState,
        legal_actions: list[Action],
        database: CardDatabase,
    ) -> Action:
        ...
