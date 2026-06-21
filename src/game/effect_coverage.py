from __future__ import annotations

import json
from pathlib import Path

from .data import load_card_database


ROOT = Path(__file__).resolve().parents[2]
OUTPUT_PATH = ROOT / "data" / "processed" / "effect_coverage.json"


def classify_card(card) -> str:
    if card.implementation_status == "implemented":
        return "implemented"
    if card.power or card.effect_id or any(token in card.text.lower() for token in ["возьми", "нанеси", "накрути"]):
        return "partial"
    return "not_implemented"


def build_coverage_report() -> dict:
    database = load_card_database()
    cards = list(database.cards.values())
    by_status = {"implemented": 0, "partial": 0, "not_implemented": 0}
    rows = []
    for card in cards:
        status = classify_card(card)
        by_status[status] += 1
        rows.append(
            {
                "id": card.id,
                "name": card.name,
                "class": card.card_class,
                "status": status,
                "attack": card.attack,
                "defense": card.defense,
                "ongoing": card.ongoing,
                "text": card.text,
            }
        )

    not_implemented = [row for row in rows if row["status"] == "not_implemented"]
    report = {
        "total_cards": len(cards),
        "implemented": by_status["implemented"],
        "partial": by_status["partial"],
        "not_implemented": by_status["not_implemented"],
        "attack_cards": sum(1 for card in cards if card.attack),
        "defense_cards": sum(1 for card in cards if card.defense),
        "ongoing_cards": sum(1 for card in cards if card.ongoing),
        "top_20_not_implemented": not_implemented[:20],
        "cards": rows,
    }
    return report


def write_coverage_report(path: Path = OUTPUT_PATH) -> dict:
    report = build_coverage_report()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main() -> None:
    report = write_coverage_report()
    summary = {
        key: report[key]
        for key in [
            "total_cards",
            "implemented",
            "partial",
            "not_implemented",
            "attack_cards",
            "defense_cards",
            "ongoing_cards",
        ]
    }
    summary["output"] = str(OUTPUT_PATH)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
