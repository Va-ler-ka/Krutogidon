from __future__ import annotations

from src.game.effect_coverage import build_coverage_report, write_coverage_report


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
