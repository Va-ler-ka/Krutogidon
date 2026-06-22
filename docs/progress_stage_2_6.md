# Отчет по этапу 2.6

## Сделано

- Добавлен `data/processed/deck_manifest.json`.
- Добавлена валидация manifest и сборка стопок из физических количеств.
- Введен `CardInstance`; игровые зоны постепенно переведены на `instance_id`.
- Стартовые колоды собираются как физические копии: 6 знаков, 1 палочка, 3 пшика на игрока.
- Шальная магия и вялые палочки имеют по 16 физических копий.
- Дохлые колдуны создаются как `player_count * 4`.
- Вум всегда первая открытая легенда.
- Количество легенд зависит от числа игроков: 9/8/7/6 для 2/3/4/5 игроков.
- Фамильяр начинает под планшетом, покупается в сброс и защищает только когда физическая карта находится на руке.
- Добавлен `src.game.card_text` для секций текста.
- Coverage стал секционным, честнее различает `no_effect`, `partial`, `not_implemented`, `implemented_with_tests`.
- Добавлен Markdown coverage: `docs/effect_coverage.md`.
- Добавлен replay/debug log через `--replay-dir`.
- Добавлен CLI-флаг `--strict`.

## Измененные модули

- `src/game/models.py`
- `src/game/setup.py`
- `src/game/engine.py`
- `src/game/effects.py`
- `src/game/legal_actions.py`
- `src/game/effect_coverage.py`
- `src/game/simulate.py`
- `src/game/scoring.py`
- `src/game/triggers.py`

## Новые модули

- `src/game/deck_manifest.py`
- `src/game/instances.py`
- `src/game/card_text.py`
- `src/game/mayhem.py`
- `src/game/replay.py`

## Добавленные тесты

- `test_deck_manifest.py`
- `test_card_instances.py`
- `test_card_text.py`
- `test_familiars.py`
- `test_replay.py`
- `test_strict_mode.py`
- `test_effect_patterns.py`

## Что стало ближе к правилам

- Физические копии карт позволяют корректно моделировать несколько копий одной карты.
- Вум и размер стопки легенд соответствуют плану stage 2.6.
- Фамильяр больше не является пассивным объектом после покупки.
- Defense window использует только defense text.
- Обычный розыгрыш не применяет defense text.
- Coverage показывает секции и проблемные карты.

## Все еще не реализовано

- Полный эффект большинства уникальных карт.
- Полный выбор карт для сброса/уничтожения/получения.
- Полные свойства и VP/scoring-эффекты.
- Replay playback.
- Официальные тиражи основной колоды, если они отличаются от текущей manifest-модели.

## Блокеры этапа 3

- Нужны scripted-агенты и эвристики поверх legal actions.
- Нужен observation/action encoder.
- Желательно реализовать больше конкретных effect patterns и снизить `not_implemented`.
- Нужен replay-анализ для отладки стратегий.

## Рекомендации для этапа 2.7

- Добавить HeuristicAgent/GreedyBuyAgent/AggressiveAgent.
- Зафиксировать observation model без скрытой информации.
- Сделать replay playback или хотя бы replay summarizer.
- Продолжить реализацию card effects по данным `effect_coverage`.
