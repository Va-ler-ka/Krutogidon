from __future__ import annotations

from .models import GameState


SELF = "self"
CHOSEN_WIZARD = "chosen_wizard"
CHOSEN_ENEMY = "chosen_enemy"
ALL_ENEMIES = "all_enemies"
ALL_WIZARDS = "all_wizards"
LEFT_ENEMY = "left_enemy"
RIGHT_ENEMY = "right_enemy"
LEFT_OR_RIGHT_ENEMY = "left_or_right_enemy"
WEAKEST_ENEMY = "weakest_enemy"
STRONGEST_ENEMY = "strongest_enemy"
ENEMIES_WEAKER_THAN_SELF = "enemies_weaker_than_self"
ENEMIES_STRONGER_THAN_SELF = "enemies_stronger_than_self"


def target_candidates(state: GameState, actor_id: int, selector: str) -> list[int]:
    if selector == SELF:
        return [actor_id]
    if selector == CHOSEN_WIZARD:
        return [player.id for player in state.players]
    if selector == ALL_WIZARDS:
        return [player.id for player in state.players]
    enemies = [player.id for player in state.players if player.id != actor_id]
    if selector in {CHOSEN_ENEMY, ALL_ENEMIES}:
        return enemies
    if selector == LEFT_ENEMY:
        return [_neighbor_enemy(state, actor_id, -1)]
    if selector == RIGHT_ENEMY:
        return [_neighbor_enemy(state, actor_id, 1)]
    if selector == LEFT_OR_RIGHT_ENEMY:
        left = _neighbor_enemy(state, actor_id, -1)
        right = _neighbor_enemy(state, actor_id, 1)
        return sorted(set([left, right]))
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
    if selector in {CHOSEN_ENEMY, CHOSEN_WIZARD, LEFT_OR_RIGHT_ENEMY, WEAKEST_ENEMY, STRONGEST_ENEMY}:
        return len(candidates) > 1
    return False


def parse_selector_from_text(text: str, *, default: str = CHOSEN_ENEMY) -> str:
    lower = text.lower()
    if "каждому колдун" in lower or "каждый колдун" in lower or "каждого колдун" in lower:
        return ALL_WIZARDS
    if "каждому враг" in lower or "каждый враг" in lower or "каждого враг" in lower:
        return ALL_ENEMIES
    if "правому или левому враг" in lower or "левому или правому враг" in lower:
        return LEFT_OR_RIGHT_ENEMY
    if "левому враг" in lower:
        return LEFT_ENEMY
    if "правому враг" in lower:
        return RIGHT_ENEMY
    if "самому хил" in lower or "с минимум" in lower:
        return WEAKEST_ENEMY
    if "самому могуч" in lower or "с максимум" in lower:
        return STRONGEST_ENEMY
    if "врагам хилее" in lower or "врагу хилее" in lower:
        return ENEMIES_WEAKER_THAN_SELF
    if "врагам могучее" in lower or "врагу могучее" in lower:
        return ENEMIES_STRONGER_THAN_SELF
    if "выбранному колдун" in lower or "выбранный колдун" in lower:
        return CHOSEN_WIZARD
    if "выбранному враг" in lower or "выбранный враг" in lower:
        return CHOSEN_ENEMY
    return default


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
