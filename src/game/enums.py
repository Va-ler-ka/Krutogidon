from __future__ import annotations

from enum import StrEnum


class CardClass(StrEnum):
    WIZARD = "Волшебник"
    SPELL = "Заклинание"
    TREASURE = "Сокровище"
    CREATURE = "Тварь"
    PLACE = "Место"
    LEGEND = "Легенда"
    FAMILIAR = "Фамильяр"
    STARTER = "Затравка"
    WILD_MAGIC = "Шальная магия"
    SERVICE = "Служебная карта"
    MAYHEM = "Беспредел"


class GamePhase(StrEnum):
    START_OF_TURN = "start_of_turn"
    MAIN = "main"
    RESOLVING_EFFECT = "resolving_effect"
    CHOOSE_TARGET = "choose_target"
    DEFENSE_WINDOW = "defense_window"
    BUY = "buy"
    END_OF_TURN = "end_of_turn"
    LEGEND_REVEAL = "legend_reveal"
    GAME_OVER = "game_over"


class ActionType(StrEnum):
    PLAY_CARD = "play_card"
    BUY_MARKET_CARD = "buy_market_card"
    BUY_CARD = "buy_market_card"
    DEFEAT_LEGEND = "defeat_legend"
    BUY_WILD_MAGIC = "buy_wild_magic"
    BUY_FAMILIAR = "buy_familiar"
    CHOOSE_TARGET = "choose_target"
    USE_DEFENSE = "use_defense"
    DECLINE_DEFENSE = "decline_defense"
    END_TURN = "end_turn"
    NOOP = "noop"
