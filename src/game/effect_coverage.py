from __future__ import annotations

import json
import os
from pathlib import Path
from uuid import uuid4

from .card_text import parse_card_text
from .data import load_card_database
from .effects import has_unparsed_complex_text
from .implemented_patterns import IMPLEMENTED_WITH_TESTS_CARD_IDS


ROOT = Path(__file__).resolve().parents[2]
OUTPUT_PATH = ROOT / "data" / "processed" / "effect_coverage.json"
MARKDOWN_PATH = ROOT / "docs" / "effect_coverage.md"
STATUSES = [
    "implemented",
    "implemented_with_tests",
    "partial_safe",
    "partial_unsafe",
    "not_implemented",
    "no_effect",
    "data_error",
]


def classify_card(card) -> str:
    sections = parse_card_text(card.text)
    if not card.name or not card.card_class:
        return "data_error"
    normalized = (card.text or "").strip().lower()
    if normalized in {"", "(эффекта нет.)", "(эффекта нет)"}:
        return "no_effect"
    if card.id in IMPLEMENTED_WITH_TESTS_CARD_IDS and (card.id == "беспредел_10" or not has_unparsed_complex_text(card)):
        return "implemented_with_tests"
    if card.implementation_status == "implemented":
        return "implemented"
    supported = any(
        token in (sections.main_text + " " + (sections.attack_text or "") + " " + (sections.defense_text or "")).lower()
        for token in ["мощ", "возьми", "нанеси", "накрути", "получает вялую палочку", "сброс"]
    )
    if supported:
        return "partial_unsafe" if has_unparsed_complex_text(card) else "partial_safe"
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
                "coverage_reason": coverage_reason(card, status),
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
    partial_unsafe = [row for row in rows if row["status"] == "partial_unsafe"]
    data_errors = [row for row in rows if row["status"] == "data_error"]
    implementedish = by_status["implemented"] + by_status["implemented_with_tests"]
    implemented_or_partial = (
        implementedish + by_status["partial_safe"] + by_status["partial_unsafe"] + by_status["no_effect"]
    )
    total = len(cards)
    report = {
        "total_cards": total,
        "statuses": by_status,
        "implemented": by_status["implemented"],
        "implemented_with_tests": by_status["implemented_with_tests"],
        "partial_safe": by_status["partial_safe"],
        "partial_unsafe": by_status["partial_unsafe"],
        "partial": by_status["partial_safe"] + by_status["partial_unsafe"],
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
        "top_partial_unsafe_cards": partial_unsafe[:20],
        "top_missing_mechanics": missing_mechanics(rows),
        "mayhem_blockers": mayhem_blockers(rows),
        "pending_choice_blockers": pending_choice_blockers(rows),
        "cards_with_data_errors": data_errors,
        "cards": rows,
    }
    return report


def coverage_reason(card, status: str) -> str:
    if status == "implemented_with_tests":
        return "fully covered by tested basic effect patterns"
    if status == "no_effect":
        return "explicit no-effect card"
    if status == "partial_safe":
        return "supported primitives found; remaining text is treated as non-state-changing"
    if status == "partial_unsafe":
        return "contains at least one supported primitive plus unresolved text"
    if status == "data_error":
        return "missing required card metadata"
    if status == "implemented":
        return "marked implemented in source data"
    return "no supported full-card implementation yet"


def missing_mechanics(rows: list[dict]) -> list[dict]:
    counters: dict[str, int] = {}
    needles = {
        "destroy_or_choose_specific_card": ["уничтож", "выбери", "посмотри"],
        "conditional_cost_or_zone_logic": ["если", "стоимость", "стопк"],
        "ongoing_trigger": ["постоянк", "каждый раз", "когда"],
        "scaling_damage_or_power": ["за кажд", "столько"],
        "dead_wizard_token_choice": ["жетон"],
        "mayhem_or_group_attack": ["беспредел", "группов"],
    }
    for row in rows:
        if row["status"] not in {"partial_unsafe", "not_implemented"}:
            continue
        lower = str(row["text"]).lower()
        for mechanic, tokens in needles.items():
            if any(token in lower for token in tokens):
                counters[mechanic] = counters.get(mechanic, 0) + 1
    return [
        {"mechanic": mechanic, "count": count}
        for mechanic, count in sorted(counters.items(), key=lambda item: item[1], reverse=True)
    ]


def mayhem_blockers(rows: list[dict]) -> list[dict]:
    return [
        row
        for row in rows
        if row["class"] == "Беспредел" and row["status"] in {"partial_unsafe", "not_implemented"}
    ]


def pending_choice_blockers(rows: list[dict]) -> list[dict]:
    tokens = ["уничтож", "сброс", "получи", "выбери", "раскрой"]
    return [
        row
        for row in rows
        if row["status"] in {"partial_unsafe", "not_implemented"}
        and any(token in str(row["text"]).lower() for token in tokens)
    ]


def write_coverage_report(path: Path = OUTPUT_PATH, markdown_path: Path | None = None) -> dict:
    report = build_coverage_report()
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(path, json.dumps(report, ensure_ascii=False, indent=2))
    if markdown_path is None and path == OUTPUT_PATH:
        markdown_path = MARKDOWN_PATH
    if markdown_path is not None:
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(markdown_path, render_markdown(report))
    return report


def atomic_write_text(path: Path, text: str) -> None:
    tmp_path = path.with_name(f"{path.name}.{os.getpid()}.{uuid4().hex}.tmp")
    try:
        tmp_path.write_text(text, encoding="utf-8")
        tmp_path.replace(path)
    except PermissionError:
        if tmp_path.exists():
            tmp_path.unlink()
        path.write_text(text, encoding="utf-8")


def render_markdown(report: dict) -> str:
    lines = [
        "# Effect Coverage",
        "",
        f"- Total cards: {report['total_cards']}",
        f"- Implemented: {report['implemented']}",
        f"- Implemented with tests: {report['implemented_with_tests']}",
        f"- Partial safe: {report['partial_safe']}",
        f"- Partial unsafe: {report['partial_unsafe']}",
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
    lines.extend(["", "## Mayhem Blockers", ""])
    for row in report["mayhem_blockers"][:20]:
        lines.append(f"- `{row['id']}` - {row['name']} ({row['status']}): {row['coverage_reason']}")
    lines.extend(["", "## Pending Choice Blockers", ""])
    for row in report["pending_choice_blockers"][:20]:
        lines.append(f"- `{row['id']}` - {row['name']} ({row['status']}): {row['coverage_reason']}")
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
        "partial_safe",
        "partial_unsafe",
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
