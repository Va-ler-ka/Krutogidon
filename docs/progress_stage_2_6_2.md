# Отчет по этапу 2.6.2

## Сделано

- Исправлен scoring жетонов дохлого колдуна: каждый ЖДК теперь дает `-3 VP`.
- Добавлен `GameConfig.max_health = 25`; лечение через `Heal` больше не поднимает здоровье выше cap.
- Смерть возвращает игрока к `death_reset_health = 20`, логируется без старого TODO про уточнение правила.
- Добавлен `SourceKind` в `EffectRequest`: player card, player mayhem, market mayhem, legend group attack, self, system.
- Обычная атака игрока, групповая атака легенды и damage-беспределы проходят через единый source-aware damage/death pipeline.
- Групповая атака легенды теперь не имеет player-attacker, не redirectable и не выдает Главный приз.
- Если групповая атака легенды открывает `DEFENSE_WINDOW` во время end-turn reveal, ход не перескакивает в `MAIN`; переход к следующему игроку откладывается до завершения атаки.
- Добавлен `GameState.trophy_controller_id`; Главный приз выдается за убийство врага источником `PLAYER_CARD` или `PLAYER_MAYHEM`, но не за self kill, market mayhem или group attack.
- Контроллер Главного приза на конце хода добирает до 6 и временно auto-discards одну карту с явным логом.
- Familiar redirect против non-player атаки логирует ignored redirect и не наносит лишний урон источнику.
- `effect_coverage` разделяет `partial_safe` и `partial_unsafe`; `implemented_with_tests` теперь требует явный registry `src/game/implemented_patterns.py`.
- `replay_summary` показывает source_kind, deaths_by_source_kind, trophy_changes, group attacks, defense/redirect counters, partial_unsafe и not_implemented diagnostics.

## Проверки

- Baseline до изменений:
  - `pytest`
  - `python -m src.game.validate_manifest`
  - `python -m src.game.effect_coverage`
  - `python -m src.game.simulate --players 2 --games 5 --seed 100`
  - `python -m src.game.simulate --players 3 --games 10 --seed 100`
  - `python -m src.game.simulate --players 5 --games 5 --seed 100`
  - `python -m src.game.simulate --players 3 --games 1 --seed 100 --replay-dir data/replays`
- После правок:
  - `pytest` — 107 passed.
  - `python -m src.game.validate_manifest` — ok.
  - `python -m src.game.effect_coverage` — ok, `implemented_with_tests=12`, `partial_unsafe=71`.
  - `python -m src.game.simulate --players 2 --games 5 --seed 100` — ok.
  - `python -m src.game.simulate --players 3 --games 10 --seed 100` — ok.
  - `python -m src.game.simulate --players 5 --games 5 --seed 100` — ok.
  - `python -m src.game.simulate --players 3 --games 1 --seed 100 --replay-dir data/replays` — ok.
  - `python -m src.game.replay_summary data/replays/game_100_20260622_234428.json` — ok; summary reports source_kind, trophy, defenses, mayhem/group/partial diagnostics.

## Добавленные тесты

- ЖДК: `-3 VP`, `-6 VP`, tie-breaker на меньшее число ЖДК.
- Health cap: лечение ниже cap, до cap и выше cap.
- Death/trophy: reset, лог смерти, player-card kill, self kill, group attack kill, player-mayhem kill, trophy end-turn auto-discard.
- Group attack lifecycle: сохранение defense window, продолжение хода после защиты, neutral source kind, redirect ignored.
- Mayhem: market mayhem neutral source/no trophy, player mayhem can award trophy.
- Coverage: registry для `implemented_with_tests`, `partial_unsafe`, top missing mechanics.
- Replay summary: Stage 2.6.2 diagnostics present.

## Strict

`python -m src.game.simulate --players 3 --games 1 --seed 100 --strict` падает на `беспредел_10`: "Разыграй каждую атаку на картах с барахолки". Это ожидаемый `not_implemented` market mayhem эффект, не стартовая карта и не ложное падение strict.

## Что осталось до полного DoD Stage 2.6.2

- Полноценные pending choices для destroy/discard/gain и discard после Главного приза. Сейчас trophy discard временно автоматический и явно залогирован.
- Более полная mayhem pipeline: часть беспределов все еще `not_implemented` или partial.
- Replay остается summary/debug, без playback.
- `partial_safe` пока не используется содержательно: все частично разобранные state-changing карты считаются `partial_unsafe`.
- `беспредел_10` и другие сложные беспределы остаются `not_implemented`; их должен закрывать следующий проход по mayhem pipeline.

## Stage 2.7

Stage 2.7 не начат. Scripted agents и evaluation стоит делать только после закрытия оставшихся пунктов Stage 2.6.2 DoD.
