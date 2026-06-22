from __future__ import annotations

import random

from .data import load_card_database
from .deck_manifest import dead_wizard_token_count
from .instances import card_def_for, card_id_for, create_card_instance, set_owner
from .models import CardDatabase, GameConfig, GameState, PlayerState


LEGEND_RANDOM_COUNTS = {
    2: 8,
    3: 7,
    4: 6,
    5: 5,
}


def setup_game(config: GameConfig, database: CardDatabase | None = None) -> tuple[GameState, CardDatabase]:
    if not 2 <= config.player_count <= 5:
        raise ValueError("player_count must be between 2 and 5")

    database = database or load_card_database()
    if database.manifest is None:
        raise ValueError("CardDatabase has no deck manifest")
    rng = random.Random(config.seed)
    validate_required_cards(database)

    state = GameState(
        config=config,
        players=[],
        current_player_index=0,
        turn_number=1,
        market=[],
        main_deck=[],
        destroyed=[],
        legend_deck=[],
        current_legend=None,
        wild_magic_stack=[],
        weak_wand_stack=[],
        familiar_market=[],
        mayhem_discard=[],
        event_log=[],
    )

    players: list[PlayerState] = []
    familiars = list(database.familiars)
    rng.shuffle(familiars)
    for player_id in range(config.player_count):
        player = PlayerState(
            id=player_id,
            name=f"Player {player_id + 1}",
            health=config.starting_health,
            unbought_familiar_id=familiars[player_id % len(familiars)] if familiars else None,
        )
        for starter in database.manifest.starters:
            for _ in range(starter.quantity_per_player):
                player.deck.append(
                    create_card_instance(
                        state,
                        starter.card_id,
                        owner_id=player_id,
                        origin="starter",
                    )
                )
        rng.shuffle(player.deck)
        draw_cards(state, player, config.hand_size, rng)
        players.append(player)
    state.players = players

    state.main_deck = build_main_deck(state, database, rng)
    state.legend_deck, state.current_legend = build_legend_stack(state, database, config.player_count, rng)
    state.wild_magic_stack = [
        create_card_instance(state, database.manifest.wild_magic_card_id, origin="wild_magic")
        for _ in range(database.manifest.wild_magic_quantity)
    ]
    state.weak_wand_stack = [
        create_card_instance(state, database.manifest.weak_wand_card_id, origin="weak_wand")
        for _ in range(database.manifest.weak_wand_quantity)
    ]
    state.dead_wizard_stack = database.dead_wizard_tokens[: dead_wizard_token_count(database.manifest, config.player_count)]

    fill_market(state, database, rng, resolve_mayhem_effects=False)
    return state, database


def validate_required_cards(database: CardDatabase) -> None:
    missing = [name for name in ["Знак", "Палочка", "Пшик"] if name not in database.starter_cards]
    if missing:
        raise ValueError(f"Missing starter cards: {missing}")


def build_main_deck(state: GameState, database: CardDatabase, rng: random.Random) -> list[str]:
    deck: list[str] = []
    for entry in database.manifest.main_deck:
        for _ in range(entry.quantity):
            deck.append(create_card_instance(state, entry.card_id, origin="main_deck"))
    rng.shuffle(deck)
    return deck


def build_legend_stack(
    state: GameState,
    database: CardDatabase,
    player_count: int,
    rng: random.Random,
) -> tuple[list[str], str | None]:
    first_card_id = database.manifest.first_legend_card_id
    random_count = LEGEND_RANDOM_COUNTS[player_count]
    candidates = [card_id for card_id in database.legends if card_id != first_card_id]
    rng.shuffle(candidates)
    selected = candidates[:random_count]
    first_instance = create_card_instance(state, first_card_id, origin="legend")
    remaining = [
        create_card_instance(state, card_id, origin="legend")
        for card_id in selected
    ]
    return remaining, first_instance


def draw_cards(state: GameState, player: PlayerState, count: int, rng: random.Random) -> int:
    drawn = 0
    for _ in range(count):
        if not player.deck and player.discard:
            player.deck = player.discard
            player.discard = []
            rng.shuffle(player.deck)
        if not player.deck:
            break
        instance_id = player.deck.pop()
        set_owner(state, instance_id, player.id)
        player.hand.append(instance_id)
        drawn += 1
    return drawn


def fill_market(
    state: GameState,
    database: CardDatabase,
    rng: random.Random,
    *,
    resolve_mayhem_effects: bool = True,
) -> None:
    from .mayhem import resolve_mayhem

    while len(state.market) < state.config.market_size:
        if not state.main_deck:
            state.game_over = True
            state.end_reason = "main_deck_empty"
            return
        instance_id = state.main_deck.pop()
        card = card_def_for(state, database, instance_id)
        if card.card_class == "Беспредел":
            state.mayhem_discard.append(instance_id)
            if resolve_mayhem_effects:
                resolve_mayhem(state, database, instance_id, rng)
            else:
                state.event_log.append(f"Беспредел раскрыт при начальном setup без эффекта: {card.name}")
            continue
        state.market.append(instance_id)
