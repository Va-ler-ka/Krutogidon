# План этапа 2.6.1

## Текущее состояние

- Stage 2.6 запушен в `origin/main` коммитом `0771608`.
- Есть `CardInstance`, manifest, секции текста, replay/debug log, strict mode и improved coverage.
- Симуляции в `strict=False` проходят.
- Strict mode сейчас полезен частично: падает на `Палочке`, хотя стартовые карты должны быть полностью реализованы.

## Найденные проблемы

- Основная колода в manifest содержит по 1 копии каждой уникальной карты, всего 84, а должна иметь 124 физические карты.
- Manifest не валидирует группы: 26 беспределов x1, 18 singleton non-mayhem, 40 double unique, 80 double physical.
- Групповая атака легенды исключает активного игрока, хотя должна применять эффект ко всем колдунам.
- Порядок групповой атаки не зафиксирован как "со следующего игрока по часовой".
- `GameConfig` всё еще содержит старые `weak_wand_count`, `wild_magic_count`, `dead_wizard_token_limit`.
- Targeting parser распознает мало формулировок.
- `Палочка` не полностью реализована: условный добор 2 карт при убийстве отсутствует, strict падает.
- Coverage держит слишком мало `implemented_with_tests`.
- Replay создается, но нет summarizer-команды.
- Документация частично описывает stage 2.6, но не уточнения 2.6.1.

## Модули, которые будут изменены

- `data/processed/deck_manifest.json`
- `src/game/deck_manifest.py`
- `src/game/validate_manifest.py`
- `src/game/models.py`
- `src/game/setup.py`
- `src/game/engine.py`
- `src/game/effects.py`
- `src/game/targeting.py`
- `src/game/effect_coverage.py`
- `src/game/replay_summary.py`
- `src/game/simulate.py`
- Документация в `README.md` и `docs/*`.

## Тесты, которые будут добавлены/расширены

- Manifest exact counts and mismatch report.
- Group attack targets/order/defense.
- Starter cards in strict mode, including `Палочка` kill draw.
- GameConfig manifest-count precedence.
- Targeting parser selectors.
- Coverage thresholds and status reasons.
- Replay summary parsing and counters.

## Не входит в этап 2.6.1

- RL, Gymnasium/PettingZoo, scripted-agent evaluation.
- UI/API.
- Полная реализация всех уникальных карт.
- Replay playback.
- Ручная переразметка `cards_full.xlsx`.

## Риски

- Официальные тиражи основной колоды выводятся из правил stage 2.6.1 и текущих данных; если `cards_full.xlsx` изменится, manifest validation должен явно показать расхождение.
- Условие `Палочки` "если он от этого подох" зависит от текущей временной модели смерти и dead wizard token.
- Strict mode может начать падать позже на следующих сложных картах, но не должен падать на стартовых.
