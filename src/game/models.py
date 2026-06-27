from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any

from .enums import ActionType, GamePhase


@dataclass(frozen=True)
class CardDefinition:
    id: str
    name: str
    card_class: str
    text: str
    cost: int | None = None
    victory_points: int = 0
    power: int = 0
    keywords: tuple[str, ...] = ()
    attack: bool = False
    defense: bool = False
    ongoing: bool = False
    group_attack: bool = False
    source_sheet: str = ""
    source_file: str = ""
    effect_id: str | None = None
    implementation_status: str = "not_implemented"


@dataclass
class CardInstance:
    instance_id: str
    card_id: str
    owner_id: int | None
    origin: str | None = None


@dataclass
class CardDatabase:
    cards: dict[str, CardDefinition]
    mayhem_cards: list[CardDefinition]
    legends: list[str]
    familiars: list[str]
    main_deck_cards: list[str]
    starter_cards: dict[str, str]
    wild_magic_id: str | None
    weak_wand_id: str | None
    dead_wizard_tokens: list[str] = field(default_factory=list)
    manifest: Any | None = None

    def by_name(self, name: str) -> CardDefinition:
        for card in self.cards.values():
            if card.name == name:
                return card
        raise KeyError(name)


@dataclass
class PlayerState:
    id: int
    name: str
    health: int = 20
    deck: list[str] = field(default_factory=list)
    hand: list[str] = field(default_factory=list)
    discard: list[str] = field(default_factory=list)
    played: list[str] = field(default_factory=list)
    ongoing: list[str] = field(default_factory=list)
    destroyed: list[str] = field(default_factory=list)
    dead_wizard_tokens: list[str] = field(default_factory=list)
    unbought_familiar_id: str | None = None
    familiar_purchased: bool = False
    familiar: str | None = None
    power: int = 0
    defeated_legends: int = 0
    has_defeated_legend_this_turn: bool = False
    next_gained_card_to_top_deck: bool = False


class SourceKind(StrEnum):
    PLAYER_CARD = "player_card"
    PLAYER_MAYHEM = "player_mayhem"
    MARKET_MAYHEM = "market_mayhem"
    LEGEND_GROUP_ATTACK = "legend_group_attack"
    DEAD_WIZARD_TOKEN = "dead_wizard_token"
    SELF = "self"
    SYSTEM = "system"


class PendingChoiceType(StrEnum):
    CHOOSE_TARGET = "choose_target"
    USE_OR_DECLINE_DEFENSE = "use_or_decline_defense"
    DISCARD_CARD = "discard_card"
    DESTROY_CARD = "destroy_card"
    GAIN_CARD = "gain_card"
    MAYHEM_CHOICE = "mayhem_choice"
    TROPHY_DISCARD = "trophy_discard"
    CHOOSE_MARKET_ATTACK_TARGET = "choose_market_attack_target"
    CHOOSE_CARD_TO_PLAY_FROM_MARKET = "choose_card_to_play_from_market"


@dataclass
class EffectRequest:
    source_card_id: str
    source_player_id: int | None
    effect_type: str
    amount: int = 0
    target_player_ids: list[int] = field(default_factory=list)
    current_target_index: int = 0
    selector: str = "chosen_enemy"
    is_attack: bool = False
    group: bool = False
    source_kind: SourceKind = SourceKind.PLAYER_CARD
    source_card_instance_id: str | None = None
    defense_allowed: bool = True
    redirectable: bool = True
    already_redirected: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PendingChoice:
    choice_type: str
    actor_id: int
    choice_id: str = ""
    source_player_id: int | None = None
    source_card_id: str | None = None
    source_card_instance_id: str | None = None
    source_kind: SourceKind | None = None
    candidates: list[int] = field(default_factory=list)
    options: list[dict[str, Any]] = field(default_factory=list)
    min_choices: int = 1
    max_choices: int = 1
    effect: EffectRequest | None = None
    prompt: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class GameConfig:
    player_count: int = 2
    seed: int | None = None
    strict: bool = False
    starting_health: int = 20
    max_health: int = 25
    hand_size: int = 5
    market_size: int = 5
    legend_count: int | None = None
    death_reset_health: int = 20
    max_turns: int = 500


@dataclass(frozen=True)
class Action:
    type: ActionType
    card_id: str | None = None
    instance_id: str | None = None
    market_index: int | None = None
    target_player: int | None = None
    actor_id: int | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    description: str = ""


@dataclass
class TurnContext:
    player_id: int
    played_cards: list[str] = field(default_factory=list)
    unresolved_effects: list[str] = field(default_factory=list)


@dataclass
class GameState:
    config: GameConfig
    players: list[PlayerState]
    current_player_index: int
    turn_number: int
    market: list[str]
    main_deck: list[str]
    destroyed: list[str]
    legend_deck: list[str]
    current_legend: str | None
    wild_magic_stack: list[str]
    weak_wand_stack: list[str]
    familiar_market: list[str]
    mayhem_discard: list[str]
    event_log: list[str]
    card_instances: dict[str, CardInstance] = field(default_factory=dict)
    next_instance_seq: int = 0
    phase: GamePhase = GamePhase.MAIN
    pending_choice: PendingChoice | None = None
    effect_queue: list[EffectRequest] = field(default_factory=list)
    dead_wizard_stack: list[str] = field(default_factory=list)
    trophy_controller_id: int | None = None
    pending_turn_advance: bool = False
    pending_market_refill: bool = False
    pending_market_attack_queue: list[dict[str, Any]] = field(default_factory=list)
    game_over: bool = False
    winner_ids: list[int] = field(default_factory=list)
    end_reason: str | None = None

    @property
    def current_player(self) -> PlayerState:
        return self.players[self.current_player_index]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
