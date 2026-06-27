from __future__ import annotations

from src.game.effect_coverage import build_coverage_report, write_coverage_report
from src.game.implemented_patterns import IMPLEMENTED_WITH_TESTS_CARD_IDS


def test_effect_coverage_report_has_required_counts(tmp_path) -> None:
    report = build_coverage_report()

    assert report["total_cards"] > 0
    assert report["attack_cards"] > 0
    assert report["defense_cards"] > 0
    assert "top_20_not_implemented" in report

    output = tmp_path / "effect_coverage.json"
    written = write_coverage_report(output)
    assert written["total_cards"] == report["total_cards"]
    assert output.exists()


def test_no_effect_cards_are_not_not_implemented() -> None:
    report = build_coverage_report()
    pshik = next(row for row in report["cards"] if row["name"] == "Пшик")

    assert pshik["status"] == "no_effect"


def test_coverage_counts_sections() -> None:
    report = build_coverage_report()

    assert report["group_attack_cards"] > 0
    assert report["cards_with_multiple_sections"] > 0


def test_coverage_outputs_markdown(tmp_path) -> None:
    json_path = tmp_path / "coverage.json"
    md_path = tmp_path / "coverage.md"

    write_coverage_report(json_path, md_path)

    assert json_path.exists()
    assert md_path.exists()


def test_implemented_with_tests_status_supported() -> None:
    report = build_coverage_report()

    assert "implemented_with_tests" in report["statuses"]
    assert report["implemented_with_tests"] >= 12
    assert all("coverage_reason" in row for row in report["cards"])


def test_implemented_with_tests_requires_registry_entry() -> None:
    report = build_coverage_report()

    implemented_rows = [row for row in report["cards"] if row["status"] == "implemented_with_tests"]

    assert implemented_rows
    assert all(row["id"] in IMPLEMENTED_WITH_TESTS_CARD_IDS for row in implemented_rows)


def test_coverage_reports_partial_unsafe_and_missing_mechanics() -> None:
    report = build_coverage_report()

    assert "partial_safe" in report["statuses"]
    assert "partial_unsafe" in report["statuses"]
    assert report["partial_unsafe"] > 0
    assert report["top_partial_unsafe_cards"]
    assert report["top_missing_mechanics"]


def test_coverage_reports_mayhem_and_pending_choice_blockers() -> None:
    report = build_coverage_report()

    assert "mayhem_blockers" in report
    assert "pending_choice_blockers" in report
    assert all(row["id"] != "беспредел_10" for row in report["mayhem_blockers"])
    assert report["pending_choice_blockers"]
