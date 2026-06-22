from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.agents.random_agent import RandomAgent

from .models import GameConfig
from .replay import action_to_dict, write_replay
from .scoring import score_player
from .setup import setup_game
from .engine import GameEngine


def run_one_game(
    *,
    players: int,
    seed: int | None,
    max_turns: int,
    strict: bool = False,
    replay_dir: Path | None = None,
) -> dict:
    config = GameConfig(player_count=players, seed=seed, max_turns=max_turns, strict=strict)
    state, database = setup_game(config)
    engine = GameEngine(state, database)
    agents = [RandomAgent(seed=(seed or 0) + index) for index in range(players)]
    action_log: list[dict] = []

    while not state.game_over:
        legal_actions = engine.legal_actions()
        actor_id = legal_actions[0].actor_id if legal_actions and legal_actions[0].actor_id is not None else state.current_player_index
        agent = agents[actor_id]
        action = agent.choose_action(state, legal_actions, database)
        action_log.append(
            {
                "turn": state.turn_number,
                "phase": state.phase,
                "actor_id": actor_id,
                "hand": list(state.players[actor_id].hand),
                "action": action_to_dict(action),
            }
        )
        engine.step(action)

    result = {
        "seed": seed,
        "turns": state.turn_number,
        "end_reason": state.end_reason,
        "winner_ids": state.winner_ids,
        "scores": [score_player(player, database, state) for player in state.players],
    }
    if replay_dir is not None:
        result["replay_path"] = str(
            write_replay(
                replay_dir=replay_dir,
                seed=seed,
                config=config,
                state=state,
                actions=action_log,
                database=database,
            )
        )
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Simulate Krutagidon games.")
    parser.add_argument("--players", type=int, default=3)
    parser.add_argument("--games", type=int, default=1)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--max-turns", type=int, default=500)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--replay-dir", type=Path, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    results = [
        run_one_game(players=args.players, seed=args.seed + game_index, max_turns=args.max_turns)
        if not args.strict and args.replay_dir is None
        else run_one_game(
            players=args.players,
            seed=args.seed + game_index,
            max_turns=args.max_turns,
            strict=args.strict,
            replay_dir=args.replay_dir,
        )
        for game_index in range(args.games)
    ]
    print(json.dumps({"games": len(results), "results": results}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
