from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import CardDatabase


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = ROOT / "data" / "processed" / "deck_manifest.json"
EXPECTED_MAIN_DECK_PHYSICAL_COUNT = 124
EXPECTED_MAYHEM_UNIQUE_COUNT = 26
EXPECTED_SINGLETON_NON_MAYHEM_COUNT = 18
EXPECTED_DOUBLE_UNIQUE_COUNT = 40
EXPECTED_DOUBLE_PHYSICAL_COUNT = 80


@dataclass(frozen=True)
class ManifestEntry:
    card_id: str
    quantity: int


@dataclass(frozen=True)
class StarterEntry:
    card_id: str
    quantity_per_player: int


@dataclass(frozen=True)
class DeckManifest:
    main_deck: tuple[ManifestEntry, ...]
    starters: tuple[StarterEntry, ...]
    wild_magic_card_id: str
    wild_magic_quantity: int
    weak_wand_card_id: str
    weak_wand_quantity: int
    first_legend_card_id: str
    legend_quantity_total: int
    dead_wizard_formula: str


def load_deck_manifest(path: Path = DEFAULT_MANIFEST) -> DeckManifest:
    if not path.exists():
        raise FileNotFoundError(
            f"Deck manifest not found: {path}. Create data/processed/deck_manifest.json."
        )
    raw = json.loads(path.read_text(encoding="utf-8"))
    return DeckManifest(
        main_deck=tuple(
            ManifestEntry(card_id=item["card_id"], quantity=int(item["quantity"]))
            for item in raw.get("main_deck", [])
        ),
        starters=tuple(
            StarterEntry(card_id=item["card_id"], quantity_per_player=int(item["quantity_per_player"]))
            for item in raw.get("starters", [])
        ),
        wild_magic_card_id=raw["wild_magic"]["card_id"],
        wild_magic_quantity=int(raw["wild_magic"]["quantity"]),
        weak_wand_card_id=raw["weak_wands"]["card_id"],
        weak_wand_quantity=int(raw["weak_wands"]["quantity"]),
        first_legend_card_id=raw["legends"]["first_legend_card_id"],
        legend_quantity_total=int(raw["legends"]["quantity_total"]),
        dead_wizard_formula=raw["dead_wizard_tokens"]["quantity_formula"],
    )


def validate_deck_manifest(manifest: DeckManifest, database: CardDatabase) -> list[str]:
    errors: list[str] = []
    for entry in manifest.main_deck:
        validate_card_quantity(errors, database, entry.card_id, entry.quantity, "main_deck")
    for entry in manifest.starters:
        validate_card_quantity(errors, database, entry.card_id, entry.quantity_per_player, "starters")
    validate_card_quantity(errors, database, manifest.wild_magic_card_id, manifest.wild_magic_quantity, "wild_magic")
    validate_card_quantity(errors, database, manifest.weak_wand_card_id, manifest.weak_wand_quantity, "weak_wands")
    if manifest.first_legend_card_id not in database.cards:
        errors.append(f"first legend not found: {manifest.first_legend_card_id}")
    elif manifest.first_legend_card_id not in database.legends:
        errors.append(f"first legend is not a legend: {manifest.first_legend_card_id}")
    if manifest.legend_quantity_total <= 0:
        errors.append("legend quantity_total must be positive")
    starter_ids = {entry.card_id for entry in manifest.starters}
    expected_starters = set(database.starter_cards.values())
    if not expected_starters.issubset(starter_ids):
        errors.append(f"missing starter cards in manifest: {sorted(expected_starters - starter_ids)}")
    errors.extend(validate_main_deck_manifest(manifest, database)["errors"])
    return errors


def expected_main_deck_quantity(card) -> int:
    if card.card_class == "Беспредел":
        return 1
    if card.card_class == "Место":
        return 1
    if card.cost in {6, 7}:
        return 1
    return 2


def validate_main_deck_manifest(manifest: DeckManifest, database: CardDatabase) -> dict[str, Any]:
    entries = {entry.card_id: entry.quantity for entry in manifest.main_deck}
    expected_ids = set(database.main_deck_cards)
    actual_ids = set(entries)
    missing = sorted(expected_ids - actual_ids)
    extra = sorted(actual_ids - expected_ids)

    mayhem: list[str] = []
    singleton: list[str] = []
    double: list[str] = []
    wrong_quantity: list[dict[str, Any]] = []

    for card_id in sorted(actual_ids & expected_ids):
        card = database.cards[card_id]
        expected_quantity = expected_main_deck_quantity(card)
        actual_quantity = entries[card_id]
        if card.card_class == "Беспредел":
            mayhem.append(card_id)
        elif expected_quantity == 1:
            singleton.append(card_id)
        else:
            double.append(card_id)
        if actual_quantity != expected_quantity:
            wrong_quantity.append(
                {
                    "card_id": card_id,
                    "name": card.name,
                    "class": card.card_class,
                    "cost": card.cost,
                    "expected": expected_quantity,
                    "actual": actual_quantity,
                }
            )

    physical_count = sum(entries.values())
    double_physical_count = sum(entries[card_id] for card_id in double if card_id in entries)
    errors: list[str] = []
    if physical_count != EXPECTED_MAIN_DECK_PHYSICAL_COUNT:
        errors.append(f"main_deck_physical_count expected 124, got {physical_count}")
    if len(mayhem) != EXPECTED_MAYHEM_UNIQUE_COUNT:
        errors.append(f"mayhem_unique_count expected 26, got {len(mayhem)}")
    if len(singleton) != EXPECTED_SINGLETON_NON_MAYHEM_COUNT:
        errors.append(f"singleton_non_mayhem_count expected 18, got {len(singleton)}")
    if len(double) != EXPECTED_DOUBLE_UNIQUE_COUNT:
        errors.append(f"double_unique_count expected 40, got {len(double)}")
    if double_physical_count != EXPECTED_DOUBLE_PHYSICAL_COUNT:
        errors.append(f"double_physical_count expected 80, got {double_physical_count}")
    if missing:
        errors.append(f"cards missing from main_deck manifest: {missing}")
    if extra:
        errors.append(f"cards not expected in main_deck manifest: {extra}")
    if wrong_quantity:
        errors.append(f"cards with wrong quantity: {wrong_quantity}")

    return {
        "errors": errors,
        "main_deck_physical_count": physical_count,
        "mayhem": mayhem,
        "singleton_non_mayhem": singleton,
        "double": double,
        "double_physical_count": double_physical_count,
        "missing": missing,
        "extra": extra,
        "wrong_quantity": wrong_quantity,
    }


def dead_wizard_token_count(manifest: DeckManifest, player_count: int) -> int:
    if manifest.dead_wizard_formula != "player_count * 4":
        raise ValueError(f"Unsupported dead wizard formula: {manifest.dead_wizard_formula}")
    return player_count * 4


def validate_card_quantity(
    errors: list[str],
    database: CardDatabase,
    card_id: str,
    quantity: int,
    section: str,
) -> None:
    if card_id not in database.cards:
        errors.append(f"{section}: unknown card_id {card_id}")
    if quantity <= 0:
        errors.append(f"{section}: quantity must be positive for {card_id}")
