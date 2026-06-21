from __future__ import annotations

from .models import GameState


SELF = "self"
CHOSEN_ENEMY = "chosen_enemy"
ALL_ENEMIES = "all_enemies"
LEFT_ENEMY = "left_enemy"
RIGHT_ENEMY = "right_enemy"
WEAKEST_ENEMY = "weakest_enemy"
STRONGEST_ENEMY = "strongest_enemy"
ENEMIES_WEAKER_THAN_SELF = "enemies_weaker_than_self"
ENEMIES_STRONGER_THAN_SELF = "enemies_stronger_than_self"


def target_candidates(state: GameState, actor_id: int, selector: str) -> list[int]:
    if selector == SELF:
        return [actor_id]
    enemies = [player.id for player in state.players if player.id != actor_id]
    if selector in {CHOSEN_ENEMY, ALL_ENEMIES}:
        return enemies
    if selector == LEFT_ENEMY:
        return [_neighbor_enemy(state, actor_id, -1)]
    if selector == RIGHT_ENEMY:
        return [_neighbor_enemy(state, actor_id, 1)]
    if selector == WEAKEST_ENEMY:
        return _health_extreme(state, enemies, weakest=True)
    if selector == STRONGEST_ENEMY:
        return _health_extreme(state, enemies, weakest=False)
    actor_health = state.players[actor_id].health
    if selector == ENEMIES_WEAKER_THAN_SELF:
        return [player_id for player_id in enemies if state.players[player_id].health < actor_health]
    if selector == ENEMIES_STRONGER_THAN_SELF:
        return [player_id for player_id in enemies if state.players[player_id].health > actor_health]
    return enemies


def needs_target_choice(state: GameState, actor_id: int, selector: str) -> bool:
    candidates = target_candidates(state, actor_id, selector)
    if selector in {CHOSEN_ENEMY, WEAKEST_ENEMY, STRONGEST_ENEMY}:
        return len(candidates) > 1
    return False


def _neighbor_enemy(state: GameState, actor_id: int, direction: int) -> int:
    if len(state.players) <= 2:
        return next(player.id for player in state.players if player.id != actor_id)
    index = actor_id
    while True:
        index = (index + direction) % len(state.players)
        if index != actor_id:
            return index


def _health_extreme(state: GameState, enemies: list[int], *, weakest: bool) -> list[int]:
    if not enemies:
        return []
    values = [(state.players[player_id].health, player_id) for player_id in enemies]
    target_health = (min if weakest else max)(health for health, _player_id in values)
    return [player_id for health, player_id in values if health == target_health]
