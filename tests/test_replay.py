from __future__ import annotations

import json

from src.game.simulate import run_one_game
from src.game.replay_summary import load_replay, summarize_replay


def test_replay_file_created(tmp_path) -> None:
    result = run_one_game(players=2, seed=56, max_turns=20, replay_dir=tmp_path)

    assert "replay_path" in result
    assert (tmp_path).glob("*.json")


def test_replay_contains_seed_actions_events_and_scores(tmp_path) -> None:
    result = run_one_game(players=2, seed=57, max_turns=20, replay_dir=tmp_path)
    payload = json.loads(open(result["replay_path"], encoding="utf-8").read())

    assert payload["seed"] == 57
    assert payload["actions"]
    assert "events" in payload
    assert "final_scores" in payload


def test_replay_summary_counts_actions_and_events(tmp_path) -> None:
    result = run_one_game(players=2, seed=75, max_turns=20, replay_dir=tmp_path)
    summary = summarize_replay(load_replay(result["replay_path"]))

    assert summary["seed"] == 75
    assert summary["actions_total"] > 0
    assert summary["events_total"] > 0
    assert summary["action_types"]
    assert summary["cards_played_count"] > 0
    assert "coverage_summary" in summary


def test_replay_summary_exposes_stage_2_6_2_diagnostics(tmp_path) -> None:
    result = run_one_game(players=3, seed=97, max_turns=60, replay_dir=tmp_path)
    summary = summarize_replay(load_replay(result["replay_path"]))

    assert "deaths_by_source_kind" in summary
    assert "trophy_changes" in summary
    assert "group_attacks_count" in summary
    assert "defenses_offered_count" in summary
    assert "defenses_used_count" in summary
    assert "defenses_declined_count" in summary
    assert "redirects_count" in summary
    assert "pending_choices_count" in summary
    assert "partial_unsafe_count" in summary
    assert "not_implemented_count" in summary
    assert "top_partial_unsafe_cards" in summary
    assert "top_not_implemented_cards" in summary
