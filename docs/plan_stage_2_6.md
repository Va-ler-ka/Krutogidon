# План этапа 2.6

## Текущее состояние

- Движок фазовый: есть `GamePhase`, `pending_choice`, `effect_queue`, `LegalActionGenerator`.
- Карты загружаются из `data/processed/cards_full.xlsx` и нормализуются в `cards_full.json`.
- Зоны игроков и общие стопки пока хранят идентификаторы `CardDefinition`, поэтому физические копии одной карты не различаются.
- Рынок, стартовые колоды, легенды, шальная магия и вялые палочки собираются модельно, без отдельного manifest-тиража.
- Фамильяр сейчас представлен как купленный отдельный объект, а не как карта, которая после покупки попадает в сброс и затем играет из колоды.
- Эффекты парсятся по всему тексту карты, без секций `main/attack/defense/ongoing/group_attack/scoring`.
- Coverage показывает грубые статусы `partial/not_implemented`, но не учитывает секции и `no_effect`.

## Найденные проблемы

- Нужны физические копии карт для replay, UI и будущего action mask.
- Legal actions должны ссылаться на конкретную физическую карту.
- Вум должен быть первой открытой легендой.
- Количество легенд зависит от числа игроков: `10 - player_count` случайных легенд плюс Вум.
- Стек дохлых колдунов должен быть `player_count * 4`.
- Шальная магия и вялые палочки должны иметь по 16 копий.
- Защита фамильяра должна быть доступна только если карта фамильяра на руке.
- Нужен replay/debug JSON по CLI-опции.
- Strict mode должен покрывать карты, беспределы, групповые атаки и trigger-shell.

## Модули, которые будут изменены

- `src/game/models.py` - `CardInstance`, зоны как физические instance IDs, manifest fields.
- `src/game/data.py` - загрузка и валидация deck manifest.
- `src/game/setup.py` - сборка стопок из manifest и создание instances.
- `src/game/engine.py` - перемещение instances, новая модель фамильяров, replay hooks, strict behavior.
- `src/game/legal_actions.py` - действия с `instance_id`.
- `src/game/effects.py` - секционный парсинг и дополнительные паттерны.
- `src/game/effect_coverage.py` - новые статусы и Markdown-отчет.
- `src/game/simulate.py` - `--strict` и `--replay-dir`.
- `src/game/scoring.py`, `src/game/serialization.py`, `src/agents/random_agent.py` - совместимость с instances.

## Новые модули

- `src/game/card_text.py` - разделение текста карт на секции.
- `src/game/deck_manifest.py` - загрузка/валидация manifest.
- `src/game/instances.py` - создание и разрешение физических копий.
- `src/game/replay.py` - запись replay/debug JSON.

## Тесты

- Deck manifest: загрузка, ссылки, количества, стартовая колода, dead wizard tokens, wild/weak stacks.
- Legends: Вум первый, число легенд по числу игроков, reveal/group attack event.
- Familiars: старт под планшетом, покупка в сброс, повторная покупка запрещена, защита только с руки.
- CardInstance: уникальность, покупка конкретной копии, уничтожение конкретной копии, legal actions с instance.
- Card text sections: main/attack/defense/ongoing/group/scoring и безопасное применение секций.
- Coverage: новые статусы, секции, JSON и Markdown.
- Effect patterns: массовый урон, weak wand, destroy, gain market, conditional, group attack.
- Mayhem: базовый урон/сброс/логирование.
- Replay: файл, seed, actions/events/scores.
- Strict: нереализованные эффекты логируются в non-strict и падают в strict.

## Риски

- Полная миграция зон на instances затронет большую часть тестов.
- В manifest нет официального тиража каждой основной карты; для основных карт будет использован явный model quantity из manifest, по умолчанию 1 на уникальную карту.
- Некоторые текстовые паттерны на русском неоднозначны; спорные эффекты останутся `partial`.
- Strict mode ожидаемо может падать в симуляции из-за большого числа нереализованных эффектов.

## Не входит в этап 2.6

- RL, Gymnasium/PettingZoo, обучение.
- UI, FastAPI, мобильный клиент.
- Полная ручная реализация всех уникальных карт.
- Replay playback.
- Точная визуализация карт.
