from __future__ import annotations

from .models import CardDefinition, CardInstance, GameState


def create_card_instance(
    state: GameState,
    card_id: str,
    *,
    owner_id: int | None = None,
    origin: str | None = None,
) -> str:
    state.next_instance_seq += 1
    instance_id = f"ci_{state.next_instance_seq:06d}"
    state.card_instances[instance_id] = CardInstance(
        instance_id=instance_id,
        card_id=card_id,
        owner_id=owner_id,
        origin=origin,
    )
    return instance_id


def card_id_for(state: GameState, card_ref: str) -> str:
    if card_ref in state.card_instances:
        return state.card_instances[card_ref].card_id
    return card_ref


def card_def_for(state: GameState, database, card_ref: str) -> CardDefinition:
    return database.cards[card_id_for(state, card_ref)]


def set_owner(state: GameState, instance_id: str, owner_id: int | None) -> None:
    if instance_id in state.card_instances:
        state.card_instances[instance_id].owner_id = owner_id


def definition_ids(state: GameState, refs: list[str]) -> list[str]:
    return [card_id_for(state, ref) for ref in refs]


def find_instance_for_card(state: GameState, refs: list[str], card_id: str) -> str | None:
    for ref in refs:
        if card_id_for(state, ref) == card_id:
            return ref
    return None
