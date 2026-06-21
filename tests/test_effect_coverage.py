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
