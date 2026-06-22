from __future__ import annotations

import json

from src.game.simulate import run_one_game


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
