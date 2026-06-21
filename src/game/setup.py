from __future__ import annotations

import random

from .data import load_card_database
from .models import CardDatabase, GameConfig, GameState, PlayerState


def setup_game(config: GameConfig, database: CardDatabase | None = None) -> tuple[GameState, CardDatabase]:
    if not 2 <= config.player_count <= 5:
        raise ValueError("player_count must be between 2 and 5")

    database = database or load_card_database()
    rng = random.Random(config.seed)
    validate_required_cards(database)

    players: list[PlayerState] = []
    for player_id in range(config.player_count):
        deck = (
            [database.starter_cards["Знак"]] * 6
            + [database.starter_cards["Палочка"]]
            + [database.starter_cards["Пшик"]] * 3
        )
        rng.shuffle(deck)
        player = PlayerState(
            id=player_id,
            name=f"Player {player_id + 1}",
            health=config.starting_health,
            deck=deck,
        )
        draw_cards(player, 5, rng)
        players.append(player)

    main_deck = list(database.main_deck_cards)
    rng.shuffle(main_deck)

    legend_deck = list(database.legends)
    rng.shuffle(legend_deck)
    legend_count = config.legend_count or config.player_count
    legend_deck = legend_deck[:legend_count]
    current_legend = legend_deck.pop(0) if legend_deck else None

    familiar_market = list(database.familiars)
    rng.shuffle(familiar_market)

    state = GameState(
        config=config,
        players=players,
        current_player_index=0,
        turn_number=1,
        market=[],
        main_deck=main_deck,
        destroyed=[],
        legend_deck=legend_deck,
        current_legend=current_legend,
        wild_magic_stack=[database.wild_magic_id] * config.wild_magic_count if database.wild_magic_id else [],
        weak_wand_stack=[database.weak_wand_id] * config.weak_wand_count if database.weak_wand_id else [],
        familiar_market=familiar_market,
        mayhem_discard=[],
        event_log=[],
        dead_wizard_stack=list(database.dead_wizard_tokens[: config.dead_wizard_token_limit]),
    )
    fill_market(state, database, rng)
    return state, database


def validate_required_cards(database: CardDatabase) -> None:
    missing = [name for name in ["Знак", "Палочка", "Пшик"] if name not in database.starter_cards]
    if missing:
        raise ValueError(f"Missing starter cards: {missing}")


def draw_cards(player: PlayerState, count: int, rng: random.Random) -> int:
    drawn = 0
    for _ in range(count):
        if not player.deck and player.discard:
            player.deck = player.discard
            player.discard = []
            rng.shuffle(player.deck)
        if not player.deck:
            break
        player.hand.append(player.deck.pop())
        drawn += 1
    return drawn


def fill_market(state: GameState, database: CardDatabase, rng: random.Random) -> None:
    while len(state.market) < state.config.market_size:
        if not state.main_deck:
            state.game_over = True
            state.end_reason = "main_deck_empty"
            return
        card_id = state.main_deck.pop()
        card = database.cards[card_id]
        if card.card_class == "Беспредел":
            state.mayhem_discard.append(card_id)
            state.event_log.append(f"Беспредел раскрыт и обработан как placeholder: {card.name}")
            continue
        state.market.append(card_id)
