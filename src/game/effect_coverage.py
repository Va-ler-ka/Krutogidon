from __future__ import annotations

import json
from pathlib import Path

from .card_text import parse_card_text
from .data import load_card_database


ROOT = Path(__file__).resolve().parents[2]
OUTPUT_PATH = ROOT / "data" / "processed" / "effect_coverage.json"
MARKDOWN_PATH = ROOT / "docs" / "effect_coverage.md"
STATUSES = [
    "implemented",
    "implemented_with_tests",
    "partial",
    "not_implemented",
    "no_effect",
    "data_error",
]


IMPLEMENTED_WITH_TESTS = {
    "затравка_знак",
    "затравка_палочка",
    "затравка_пшик",
    "служебная_карта_вялая_палочка",
}


def classify_card(card) -> str:
    sections = parse_card_text(card.text)
    if not card.name or not card.card_class:
        return "data_error"
    normalized = (card.text or "").strip().lower()
    if normalized in {"", "(эффекта нет.)", "(эффекта нет)"}:
        return "no_effect"
    if card.id in IMPLEMENTED_WITH_TESTS:
        return "implemented_with_tests"
    if card.implementation_status == "implemented":
        return "implemented"
    supported = any(
        token in (sections.main_text + " " + (sections.attack_text or "") + " " + (sections.defense_text or "")).lower()
        for token in ["мощ", "возьми", "нанеси", "накрути", "получает вялую палочку", "сброс"]
    )
    if supported:
        return "partial"
    return "not_implemented"


def build_coverage_report() -> dict:
    database = load_card_database()
    cards = list(database.cards.values())
    by_status = {status: 0 for status in STATUSES}
    rows = []
    for card in cards:
        status = classify_card(card)
        by_status[status] += 1
        sections = parse_card_text(card.text)
        section_count = sum(
            bool(value)
            for value in [
                sections.main_text,
                sections.attack_text,
                sections.defense_text,
                sections.ongoing_text,
                sections.group_attack_text,
                sections.scoring_text,
            ]
        )
        rows.append(
            {
                "id": card.id,
                "name": card.name,
                "class": card.card_class,
                "status": status,
                "attack": card.attack,
                "defense": card.defense,
                "ongoing": card.ongoing,
                "group_attack": card.group_attack,
                "has_scoring_text": sections.scoring_text is not None,
                "multiple_sections": section_count > 1,
                "sections": {
                    "main_text": sections.main_text,
                    "attack_text": sections.attack_text,
                    "defense_text": sections.defense_text,
                    "ongoing_text": sections.ongoing_text,
                    "group_attack_text": sections.group_attack_text,
                    "scoring_text": sections.scoring_text,
                },
                "text": card.text,
            }
        )

    not_implemented = [row for row in rows if row["status"] == "not_implemented"]
    data_errors = [row for row in rows if row["status"] == "data_error"]
    implementedish = by_status["implemented"] + by_status["implemented_with_tests"]
    implemented_or_partial = implementedish + by_status["partial"] + by_status["no_effect"]
    total = len(cards)
    report = {
        "total_cards": total,
        "statuses": by_status,
        "implemented": by_status["implemented"],
        "implemented_with_tests": by_status["implemented_with_tests"],
        "partial": by_status["partial"],
        "not_implemented": by_status["not_implemented"],
        "no_effect": by_status["no_effect"],
        "data_error": by_status["data_error"],
        "attack_cards": sum(1 for card in cards if card.attack),
        "defense_cards": sum(1 for card in cards if card.defense),
        "ongoing_cards": sum(1 for card in cards if card.ongoing),
        "group_attack_cards": sum(1 for card in cards if card.group_attack),
        "cards_with_scoring_text": sum(1 for row in rows if row["has_scoring_text"]),
        "cards_with_multiple_sections": sum(1 for row in rows if row["multiple_sections"]),
        "percent_implemented": round((implementedish / total) * 100, 2) if total else 0,
        "percent_implemented_or_partial": round((implemented_or_partial / total) * 100, 2) if total else 0,
        "top_unimplemented_cards": not_implemented[:20],
        "top_20_not_implemented": not_implemented[:20],
        "cards_with_data_errors": data_errors,
        "cards": rows,
    }
    return report


def write_coverage_report(path: Path = OUTPUT_PATH, markdown_path: Path = MARKDOWN_PATH) -> dict:
    report = build_coverage_report()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(render_markdown(report), encoding="utf-8")
    return report


def render_markdown(report: dict) -> str:
    lines = [
        "# Effect Coverage",
        "",
        f"- Total cards: {report['total_cards']}",
        f"- Implemented: {report['implemented']}",
        f"- Implemented with tests: {report['implemented_with_tests']}",
        f"- Partial: {report['partial']}",
        f"- Not implemented: {report['not_implemented']}",
        f"- No effect: {report['no_effect']}",
        f"- Data errors: {report['data_error']}",
        f"- Percent implemented: {report['percent_implemented']}%",
        f"- Percent implemented or partial: {report['percent_implemented_or_partial']}%",
        "",
        "## Top Unimplemented",
        "",
    ]
    for row in report["top_unimplemented_cards"]:
        lines.append(f"- `{row['id']}` - {row['name']} ({row['class']})")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    report = write_coverage_report()
    summary = {
        key: report[key]
        for key in [
            "total_cards",
            "implemented",
            "implemented_with_tests",
            "partial",
            "not_implemented",
            "no_effect",
            "data_error",
            "attack_cards",
            "defense_cards",
            "ongoing_cards",
            "group_attack_cards",
            "cards_with_scoring_text",
            "percent_implemented",
            "percent_implemented_or_partial",
        ]
    }
    summary["output"] = str(OUTPUT_PATH)
    summary["markdown"] = str(MARKDOWN_PATH)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
