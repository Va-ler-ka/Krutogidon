from __future__ import annotations

import argparse
import json

from src.agents.random_agent import RandomAgent

from .models import GameConfig
from .scoring import score_player
from .setup import setup_game
from .engine import GameEngine


def run_one_game(*, players: int, seed: int | None, max_turns: int) -> dict:
    config = GameConfig(player_count=players, seed=seed, max_turns=max_turns)
    state, database = setup_game(config)
    engine = GameEngine(state, database)
    agents = [RandomAgent(seed=(seed or 0) + index) for index in range(players)]

    while not state.game_over:
        legal_actions = engine.legal_actions()
        actor_id = legal_actions[0].actor_id if legal_actions and legal_actions[0].actor_id is not None else state.current_player_index
        agent = agents[actor_id]
        action = agent.choose_action(state, legal_actions, database)
        engine.step(action)

    return {
        "seed": seed,
        "turns": state.turn_number,
        "end_reason": state.end_reason,
        "winner_ids": state.winner_ids,
        "scores": [score_player(player, database) for player in state.players],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Simulate Krutagidon games.")
    parser.add_argument("--players", type=int, default=3)
    parser.add_argument("--games", type=int, default=1)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--max-turns", type=int, default=500)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    results = [
        run_one_game(players=args.players, seed=args.seed + game_index, max_turns=args.max_turns)
        for game_index in range(args.games)
    ]
    print(json.dumps({"games": len(results), "results": results}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
