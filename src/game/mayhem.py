from __future__ import annotations

import random
import re

from .effects import apply_damage
from .instances import card_def_for
from .models import CardDatabase, GameState


def resolve_mayhem(state: GameState, database: CardDatabase, instance_id: str, rng: random.Random) -> None:
    card = card_def_for(state, database, instance_id)
    lower = card.text.lower()
    state.event_log.append(f"Беспредел раскрыт: {card.name}")
    damage_match = re.search(r"кажд(?:ый|ому|ого).*?(\d+)\s+урон", lower)
    if damage_match:
        damage = int(damage_match.group(1))
        actor_id = state.current_player.id if state.players else 0
        for player in state.players:
            apply_damage(state, actor_id, player.id, damage)
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
