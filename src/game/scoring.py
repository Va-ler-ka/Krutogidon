from __future__ import annotations

from .instances import card_id_for
from .models import CardDatabase, GameState, PlayerState


def score_player(player: PlayerState, database: CardDatabase, state: GameState | None = None) -> int:
    zones = player.deck + player.hand + player.discard + player.played + player.ongoing
    if player.familiar:
        zones.append(player.familiar)
    card_ids = [card_id_for(state, ref) if state is not None else ref for ref in zones]
    total = sum(database.cards[card_id].victory_points for card_id in card_ids if card_id in database.cards)
    total -= len(player.dead_wizard_tokens)
    return total


def compute_winners(state: GameState, database: CardDatabase) -> list[int]:
    ranked = sorted(
        state.players,
        key=lambda player: (
            score_player(player, database, state),
            player.defeated_legends,
            -len(player.dead_wizard_tokens),
        ),
        reverse=True,
    )
    if not ranked:
        return []
    best_key = (
        score_player(ranked[0], database, state),
        ranked[0].defeated_legends,
        -len(ranked[0].dead_wizard_tokens),
    )
    return [
        player.id
        for player in ranked
        if (
            score_player(player, database, state),
            player.defeated_legends,
            -len(player.dead_wizard_tokens),
        )
        == best_key
    ]
