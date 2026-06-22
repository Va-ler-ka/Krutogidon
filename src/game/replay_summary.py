from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any


def load_replay(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Replay not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def summarize_replay(payload: dict[str, Any]) -> dict[str, Any]:
    actions = payload.get("actions", [])
    events = payload.get("events", [])
    action_types = Counter(normalize_action_type(action_payload(action).get("type", "")) for action in actions)

    event_text = "\n".join(str(event) for event in events).lower()
    source_kind_counts = Counter(extract_source_kinds(events))
    summary = {
        "seed": payload.get("seed"),
        "git_commit": payload.get("git_commit"),
        "players": payload.get("config", {}).get("player_count"),
        "turns": payload.get("turns"),
        "end_reason": payload.get("end_reason"),
        "winner_ids": payload.get("winner_ids", []),
        "final_scores": payload.get("final_scores", []),
        "actions_total": len(actions),
        "events_total": len(events),
        "action_types": dict(sorted(action_types.items())),
        "cards_played_count": action_types.get("play_card", 0),
        "cards_bought_count": (
            action_types.get("buy_market_card", 0)
            + action_types.get("buy_wild_magic", 0)
            + action_types.get("buy_familiar", 0)
        ),
        "deaths_by_source_kind": dict(sorted(source_kind_counts.items())),
        "trophy_changes": count_any(event_text, ["trophy_change"]),
        "attacks_resolved_count": count_any(event_text, ["deals", "наносит", "урон"]),
        "group_attacks_count": count_any(event_text, ["групповая атака легенды", "legend group attack"]),
        "defenses_offered_count": count_any(event_text, ["defense offered", "may defend against attack"]),
        "defenses_used_count": count_any(event_text, ["uses defense", "использует защит"]),
        "defenses_declined_count": action_types.get("decline_defense", 0),
        "redirects_count": count_any(event_text, ["redirected attack", "redirect ignored"]),
        "pending_choices_count": action_types.get("choose_target", 0),
        "deaths_count": count_any(event_text, ["receives dead wizard token", "жетон дохлого колдуна"]),
        "mayhems_revealed_count": count_any(event_text, ["беспредел раскрыт", "беспредел раскрыт"]),
        "legends_defeated_count": count_any(event_text, ["побеждает легенду", "defeats legend"]),
        "unimplemented_effects_count": count_any(event_text, ["not_implemented", "effect skipped"]),
        "not_implemented_count": count_any(event_text, ["not_implemented", "effect skipped"]),
        "partial_effects_count": count_any(event_text, ["complex text skipped", "basic parts applied"]),
        "partial_unsafe_count": count_any(event_text, ["complex text skipped", "basic parts applied", "partial_unsafe"]),
        "top_partial_unsafe_cards": top_event_sources(events, ["complex text skipped", "basic parts applied", "partial_unsafe"]),
        "top_not_implemented_cards": top_event_sources(events, ["not_implemented", "effect skipped"]),
        "coverage_summary": payload.get("coverage_summary", {}),
    }
    return summary


def normalize_action_type(value: Any) -> str:
    text = str(value)
    if "." in text:
        text = text.rsplit(".", 1)[-1]
    return text.lower()


def action_payload(action: dict[str, Any]) -> dict[str, Any]:
    nested = action.get("action")
    return nested if isinstance(nested, dict) else action


def count_any(text: str, needles: list[str]) -> int:
    return sum(text.count(needle.lower()) for needle in needles)


def extract_source_kinds(events: list[Any]) -> list[str]:
    result: list[str] = []
    for event in events:
        text = str(event)
        if "dies" not in text and "dead wizard token" not in text:
            continue
        result.extend(re.findall(r"source_kind=([a-z_]+)", text))
    return result


def top_event_sources(events: list[Any], needles: list[str]) -> list[dict[str, Any]]:
    counts: Counter[str] = Counter()
    lowered_needles = [needle.lower() for needle in needles]
    for event in events:
        text = str(event)
        lower = text.lower()
        if any(needle in lower for needle in lowered_needles):
            source = text.split(":", 1)[0]
            counts[source] += 1
    return [{"source": source, "count": count} for source, count in counts.most_common(10)]


def main(argv: list[str] | None = None) -> None:
    argv = argv if argv is not None else sys.argv[1:]
    if len(argv) != 1:
        print("Usage: python -m src.game.replay_summary <replay.json>", file=sys.stderr)
        raise SystemExit(2)
    try:
        summary = summarize_replay(load_replay(Path(argv[0])))
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
