from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path

from .effect_coverage import build_coverage_report
from .models import Action, GameConfig, GameState
from .scoring import score_player


def git_commit() -> str | None:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
    except Exception:
        return None


def action_to_dict(action: Action) -> dict:
    return {
        "type": action.type,
        "actor_id": action.actor_id,
        "card_id": action.card_id,
        "instance_id": action.instance_id,
        "market_index": action.market_index,
        "target_player": action.target_player,
        "payload": action.payload,
        "description": action.description,
    }


def write_replay(
    *,
    replay_dir: Path,
    seed: int | None,
    config: GameConfig,
    state: GameState,
    actions: list[dict],
    database,
) -> Path:
    replay_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = replay_dir / f"game_{seed}_{timestamp}.json"
    coverage = build_coverage_report()
    payload = {
        "seed": seed,
        "git_commit": git_commit(),
        "config": config.__dict__,
        "actions": actions,
        "events": state.event_log,
        "end_reason": state.end_reason,
        "winner_ids": state.winner_ids,
        "final_scores": [score_player(player, database, state) for player in state.players],
        "turns": state.turn_number,
        "coverage_summary": {
            "total_cards": coverage["total_cards"],
            "statuses": coverage["statuses"],
            "percent_implemented_or_partial": coverage["percent_implemented_or_partial"],
        },
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return path
