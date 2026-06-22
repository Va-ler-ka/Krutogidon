from __future__ import annotations

from .instances import card_def_for
from .models import CardDatabase, GameState


TRIGGER_NAMES = {
    "on_start_turn",
    "on_end_turn",
    "on_card_played",
    "on_card_bought",
    "on_damage_dealt",
    "on_enemy_killed",
}


def fire_trigger(
    state: GameState,
    database: CardDatabase,
    trigger_name: str,
    player_id: int,
    card_id: str | None = None,
) -> None:
    if trigger_name not in TRIGGER_NAMES:
        raise ValueError(f"Unknown trigger: {trigger_name}")
    player = state.players[player_id]
    for ongoing_id in player.ongoing:
        ongoing = card_def_for(state, database, ongoing_id)
        if trigger_name in ongoing.text.lower():
            state.event_log.append(f"{ongoing.name}: {trigger_name} trigger not_implemented")
    if card_id is not None:
        card = card_def_for(state, database, card_id)
        if card.ongoing:
            state.event_log.append(f"{card.name}: passive trigger shell registered")
