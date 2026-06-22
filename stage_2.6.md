# Запрос для Codex-агента: Stage 2.6 — Rule Fidelity, Deck Manifest and Effect Sections

Ты работаешь в уже существующем проекте симулятора настольной карточной игры **«Эпичные схватки боевых магов. Крутагидон»**.

Репозиторий: `https://github.com/Va-ler-ka/Krutogidon`  
Основная ветка: `origin/main`  
Текущий ориентир: после коммита `e9d0afa Implement stage 2.5 mechanics layer`

## Текущее состояние проекта

Этапы 1, 2 и 2.5 уже выполнены.

Уже есть:

- ручной перенос всех карт в `data/processed/cards_full.xlsx`;
- генерация `data/processed/cards_full.json`;
- базовый headless-движок в `src/game`;
- явные фазы игры в `GameState`;
- `LegalActionGenerator`;
- `pending target choice` и `defense window`;
- primitive effects:
  - мощь;
  - добор;
  - лечение;
  - урон;
  - сброс;
  - weak wand;
  - reveal hand;
  - composite / conditional shells;
- targeting selectors;
- базовая защита с руки;
- защита фамильяром с перенаправлением;
- постоянки как `ongoing` + trigger shell;
- беспределы не занимают рынок и логируются;
- смерть, жетоны дохлых колдунов и конец игры при пустой стопке;
- команда `python -m src.game.effect_coverage`;
- тесты проходят: `pytest`;
- симуляция проходит: `python -m src.game.simulate --players 3 --games 10 --seed 100`.

Текущий отчёт покрытия примерно такой:

```text
total_cards: 113
partial: 75
not_implemented: 38
attack_cards: 48
defense_cards: 21
ongoing_cards: 10
```

## Главная задача этапа 2.6

Не переходи к RL, обучению агентов, UI, FastAPI или мобильному интерфейсу.

Цель этапа 2.6 — сделать движок ближе к реальным правилам игры и подготовить его к следующему этапу scripted-агентов.

Фокус:

1. правильный состав колод и тиражи карт;
2. корректная модель легенд;
3. корректная модель фамильяров;
4. введение `CardInstance` или эквивалентной модели физических копий карт;
5. разделение текста карт на секции;
6. более честный отчёт покрытия эффектов;
7. реализация 20–30 ключевых карт / паттернов эффектов;
8. replay/debug log для воспроизведения партий по seed;
9. дополнительные тесты на соответствие правилам.

## Важные ограничения

- Не переписывай проект с нуля.
- Не ломай существующие команды.
- Не добавляй тяжёлые зависимости без необходимости.
- Не начинай RL.
- Не делай UI.
- Не делай FastAPI.
- Не выдумывай тексты карт.
- Не изменяй смысл данных карт без явного указания.
- Если эффект карты не реализован, он должен быть явно отражён в coverage report.
- Все изменения должны быть покрыты тестами.
- После выполнения этапа обнови документацию.

Существующие команды должны продолжать работать:

```bash
pytest
python -m src.game.simulate --players 3 --games 10 --seed 100
python -m src.game.effect_coverage
```

## Перед началом работы

Сначала изучи текущий проект:

- `README.md`
- `docs/decisions.md`
- `docs/engine_architecture.md`
- `docs/progress_stage_2_5.md`
- `data/processed/cards_full.xlsx`
- `data/processed/cards_full.json`
- `data/processed/effect_coverage.json`
- `src/game/*`
- `src/agents/*`
- `tests/*`

После анализа создай файл:

```text
docs/plan_stage_2_6.md
```

В нём опиши:

- текущее состояние;
- найденные проблемы;
- какие модули будешь менять;
- какие новые модули добавишь;
- какие тесты добавишь;
- какие риски есть;
- что не входит в этап 2.6.

Не приступай к массовым изменениям, пока не создан `docs/plan_stage_2_6.md`.

---

# 1. Deck manifest и правильные тиражи карт

## Проблема

Сейчас проект использует уникальные карты из таблицы. Но в реальной игре есть физические копии карт и фиксированные стопки.

Нужно отделить:

- `CardDefinition` — описание уникальной карты;
- физическую копию карты в партии;
- количество копий карты в конкретной стопке.

## Что сделать

Добавь один из вариантов:

### Предпочтительный вариант

Создай файл:

```text
data/processed/deck_manifest.json
```

Формат примерно такой:

```json
{
  "main_deck": [
    {
      "card_id": "slug",
      "quantity": 2
    }
  ],
  "starters": [
    {
      "card_id": "znak",
      "quantity_per_player": 6
    },
    {
      "card_id": "palochka",
      "quantity_per_player": 1
    },
    {
      "card_id": "pshik",
      "quantity_per_player": 3
    }
  ],
  "wild_magic": {
    "card_id": "shalnaya_magiya",
    "quantity": 16
  },
  "weak_wands": {
    "card_id": "vyalaya_palochka",
    "quantity": 16
  },
  "legends": {
    "quantity_total": 12,
    "first_legend_card_id": "vum"
  },
  "dead_wizard_tokens": {
    "quantity_formula": "player_count * 4"
  }
}
```

### Допустимый вариант

Добавь колонку `quantity` в `cards_full.xlsx` / нормализованный JSON и используй её для сборки стопок.

## Требования

- Не ломай текущий загрузчик Excel.
- Если `deck_manifest.json` отсутствует, создай понятную ошибку или fallback с предупреждением.
- Для стартовых карт используй реальные количества:
  - 6 знаков на игрока;
  - 1 палочка на игрока;
  - 3 пшика на игрока.
- Для шальной магии — 16 карт.
- Для вялых палочек — 16 карт.
- Для жетонов дохлых колдунов — `player_count * 4`.
- Основная колода должна собираться из manifest/quantity, а не просто из уникальных карт.
- Беспределы должны быть частью основной колоды, если так указано в данных/manifest.
- Добавь валидацию manifest:
  - все `card_id` существуют;
  - quantity положительные;
  - стартовые карты найдены;
  - шальная магия найдена;
  - вялая палочка найдена;
  - Вум найден среди легенд.

## Тесты

Добавь тесты:

- `test_deck_manifest_loads`;
- `test_deck_manifest_references_existing_cards`;
- `test_setup_uses_quantities`;
- `test_starter_deck_exact_composition`;
- `test_dead_wizard_tokens_player_count_times_four`;
- `test_wild_magic_and_weak_wand_counts`.

---

# 2. Правильная модель легенд

## Проблема

Сейчас легенды могут быть просто перемешаны. По правилам Вум должен быть первой открытой легендой, а количество остальных легенд зависит от числа игроков.

## Что сделать

Создай функцию вроде:

```python
build_legend_stack(card_db, player_count, rng) -> list[CardInstance]
```

Правило количества:

```text
2 игрока: 8 случайных легенд + Вум
3 игрока: 7 случайных легенд + Вум
4 игрока: 6 случайных легенд + Вум
5 игроков: 5 случайных легенд + Вум
```

Вум всегда должен быть первой открытой легендой.

Остальные легенды должны быть выбраны случайно из доступных легенд без Вума.

## Требования

- Вум лежит сверху стопки и открыт с начала игры.
- Остальные легенды закрыты до раскрытия.
- За ход можно победить только одну легенду.
- Новая легенда раскрывается в конце хода.
- При раскрытии создаётся событие групповой атаки.
- Если групповая атака конкретной легенды не реализована, она логируется как `not_implemented` / `partial`, но не ломает игру в `strict=False`.

## Тесты

Добавь тесты:

- `test_vum_is_first_legend`;
- `test_legend_count_by_player_count`;
- `test_only_one_legend_can_be_defeated_per_turn`;
- `test_next_legend_revealed_at_end_of_turn`;
- `test_group_attack_event_logged_on_reveal`.

---

# 3. Корректная модель фамильяров

## Проблема

Фамильяр не должен быть постоянным отдельным объектом, который всегда доступен игроку после покупки. По правилам фамильяр сначала лежит под планшетом, его эффекты не применяются. После покупки он отправляется в сброс и дальше становится обычной картой личной колоды игрока.

## Что сделать

Раздели:

```python
player.unbought_familiar_id
player.familiar_purchased
```

Или аналогичные поля.

При setup:

- у каждого игрока есть фамильяр под планшетом;
- он видим публично;
- он ещё не является картой в колоде;
- его свойства не работают.

При покупке:

- игрок тратит мощь;
- фамильяр попадает в `discard`;
- `familiar_purchased = True`;
- повторно купить того же фамильяра нельзя.

После покупки:

- фамильяр участвует в доборе, сбросе, розыгрыше, защите как обычная карта;
- защита фамильяра доступна только если карта фамильяра находится на руке;
- атака/эффект фамильяра доступна только когда карта разыграна в свой ход.

## Тесты

Добавь тесты:

- `test_familiar_starts_unbought`;
- `test_unbought_familiar_effects_do_not_apply`;
- `test_buy_familiar_puts_card_into_discard`;
- `test_familiar_cannot_be_bought_twice`;
- `test_familiar_defense_requires_card_in_hand`;
- `test_familiar_redirects_attack_only_when_used_as_defense`.

---

# 4. CardInstance / физические копии карт

## Проблема

Сейчас многие зоны могут хранить только `card_id`. Это работает для прототипа, но плохо подходит для:

- нескольких копий одной карты;
- выбора конкретной карты из руки;
- уничтожения конкретной копии;
- replay;
- UI;
- RL action masks.

## Что сделать

Введи модель:

```python
@dataclass
class CardInstance:
    instance_id: str
    card_id: str
    owner_id: int | None
    origin: str | None = None
```

Или эквивалент.

`CardDefinition` / `Card` остаётся описанием уникальной карты.

Зоны игры должны постепенно перейти на `instance_id`, `CardInstance` или `zone + index`.

Не обязательно за один шаг переписывать всё идеально. Но после этапа 2.6 действия агента должны однозначно ссылаться на конкретную карту.

## Требования

- В партии каждая физическая карта имеет уникальный `instance_id`.
- Стартовые колоды создаются из физических копий.
- Основная колода создаётся из физических копий согласно manifest/quantity.
- Покупка перемещает физическую копию из рынка в сброс.
- Сброс/уничтожение/добор работают с физическими копиями.
- Сериализация состояния содержит достаточно информации для debug.
- Legal actions ссылаются на конкретную карту через `instance_id` или `zone + index`.

## Тесты

Добавь тесты:

- `test_card_instances_are_unique`;
- `test_two_copies_same_card_have_different_instance_ids`;
- `test_buy_moves_specific_instance_to_discard`;
- `test_destroy_removes_specific_instance`;
- `test_legal_actions_reference_specific_cards`.

---

# 5. Разделение текста карт на секции

## Проблема

Сейчас простая логика может парсить весь текст карты целиком. Это опасно, потому что карта может содержать разные секции:

- основной эффект;
- атака;
- защита;
- постоянка;
- групповая атака;
- scoring / VP-эффект;
- условные эффекты.

Нужно не применять текст защиты при обычном розыгрыше и не применять основной текст как защиту.

## Что сделать

Создай модуль, например:

```text
src/game/card_text.py
```

Он должен уметь выделять секции:

```python
@dataclass
class CardTextSections:
    main_text: str
    attack_text: str | None
    defense_text: str | None
    ongoing_text: str | None
    group_attack_text: str | None
    scoring_text: str | None
    raw_text: str
```

Минимальная логика:

- всё до `Атака:` — `main_text`;
- текст после `Атака:` до следующего известного маркера — `attack_text`;
- текст после `Защита:` — `defense_text`;
- текст после `Постоянка:` — `ongoing_text`;
- текст после `Групповая атака:` — `group_attack_text`;
- фразы про «в конце игры», «победные очки», «при подсчёте» — `scoring_text`.

Поддержи русские формулировки и возможные варианты OCR/ручного ввода:

- `Атака:`
- `Защита:`
- `Постоянка:`
- `Групповая атака:`
- `В начале хода`
- `В конце хода`
- `в конце игры`
- `при подсчёте победных очков`

## Требования

- Эффекты обычного розыгрыша применяются только из `main_text` и, если карта имеет атаку, из `attack_text` через attack resolver.
- Defense window использует только `defense_text`.
- Ongoing triggers используют `ongoing_text`.
- Group attack использует только `group_attack_text`.
- Coverage report должен учитывать секции.

## Тесты

Добавь тесты:

- `test_parse_main_and_attack_sections`;
- `test_parse_defense_section`;
- `test_parse_ongoing_section`;
- `test_parse_group_attack_section`;
- `test_defense_text_not_applied_on_normal_play`;
- `test_attack_text_not_applied_without_attack_resolution`.

---

# 6. Улучшить effect coverage report

## Проблема

Сейчас отчёт может считать карту `partial`, если в тексте есть простые ключевые слова. Нужно сделать отчёт более честным и полезным.

## Что сделать

Расширь статусы:

```text
implemented
implemented_with_tests
partial
not_implemented
no_effect
data_error
```

Правила:

- `no_effect` — для карт без эффекта, например пшик / вялая палочка, если у них действительно нет эффекта.
- `implemented` — эффект реализован декларативно или через primitive.
- `implemented_with_tests` — эффект реализован и есть тест.
- `partial` — реализована только часть текста.
- `not_implemented` — эффект не реализован.
- `data_error` — проблема в данных карты.

Отчёт должен показывать:

- total cards;
- count по статусам;
- attack cards;
- defense cards;
- ongoing cards;
- group attack cards;
- cards with scoring text;
- top unimplemented cards;
- cards with data errors;
- cards whose text has multiple sections;
- percent implemented;
- percent implemented_or_partial.

Сохраняй JSON:

```text
data/processed/effect_coverage.json
```

И желательно Markdown-отчёт:

```text
docs/effect_coverage.md
```

Команда остаётся:

```bash
python -m src.game.effect_coverage
```

## Тесты

Добавь тесты:

- `test_no_effect_cards_are_not_not_implemented`;
- `test_coverage_counts_sections`;
- `test_coverage_outputs_json`;
- `test_coverage_outputs_markdown`;
- `test_implemented_with_tests_status_supported`.

---

# 7. Реализовать 20–30 ключевых карт или паттернов эффектов

## Цель

Не нужно пытаться реализовать все карты сразу. Нужно реализовать самые частотные и важные паттерны, чтобы симуляция стала более похожей на игру.

## Приоритетные паттерны

Реализуй как reusable primitives / selectors / conditions:

1. `+N мощи`;
2. `Возьми N карт`;
3. `Накрути N жизни`;
4. `Нанеси N урона выбранному врагу`;
5. `Нанеси N урона каждому врагу`;
6. `Нанеси N урона левому или правому врагу`;
7. `Нанеси N урона самому хилому врагу`;
8. `Нанеси N урона самому могучему врагу`;
9. `Получить вялую палочку`;
10. `Каждый враг получает вялую палочку`;
11. `Сбрось карту`;
12. `Выбранный враг сбрасывает карту`;
13. `Каждый враг сбрасывает карту`;
14. `Раскрой руку выбранного врага`;
15. `Уничтожь карту с руки`;
16. `Уничтожь карту из сброса`;
17. `Уничтожь карту со своей руки или из сброса`;
18. `Получить карту с барахолки`;
19. `Следующую купленную/полученную карту положи на верх колоды`;
20. `Если условие выполнено — эффект A, иначе эффект B`;
21. `Защита: избежать атаки`;
22. `Защита: избежать атаки, взять карту`;
23. `Защита: избежать атаки, накрутить жизни`;
24. `Защита фамильяра: перенаправить урон атакующему`;
25. `Постоянка: триггер на первую карту определённого типа за ход`;
26. `Постоянка: триггер в начале хода`;
27. `Постоянка: триггер в конце хода`;
28. `Групповая атака: каждый колдун получает урон`;
29. `Групповая атака: каждый колдун получает вялую палочку`;
30. `Групповая атака: каждый колдун сбрасывает карту`.

## Требования

- Эффекты должны быть reusable.
- Не делать огромный `if/else` по названиям карт.
- Для отдельных уникальных карт допустим `effect_id`, но реализация должна использовать primitives.
- Обновить `implementation.status` там, где эффект реализован.
- Добавить тесты хотя бы для 10–15 паттернов.

## Тесты

Добавь тесты:

- `test_attack_each_enemy`;
- `test_attack_left_or_right_enemy`;
- `test_give_weak_wand`;
- `test_each_enemy_gets_weak_wand`;
- `test_destroy_from_hand`;
- `test_destroy_from_discard`;
- `test_gain_card_from_market`;
- `test_next_gained_card_to_top_deck`;
- `test_conditional_effect_then_else`;
- `test_group_attack_damage_each_wizard`.

---

# 8. Беспределы: базовые паттерны

## Что сделать

Сейчас беспределы не занимают рынок и логируются. Это оставить, но добавить реализацию базовых паттернов беспредела, если они встречаются в данных:

- каждый колдун получает урон;
- каждый колдун сбрасывает карту;
- каждый колдун получает вялую палочку;
- каждый колдун раскрывает руку;
- колдун/колдуны с минимумом/максимумом ресурса получают эффект;
- применить групповую атаку текущей легенды.

Если конкретный беспредел сложный — логировать `partial` / `not_implemented`.

## Тесты

Добавь тесты:

- `test_mayhem_does_not_enter_market`;
- `test_mayhem_basic_damage_resolves`;
- `test_mayhem_basic_discard_resolves`;
- `test_mayhem_unimplemented_logged`.

---

# 9. Replay / debug log

## Цель

Для дальнейших агентов и отладки нужен воспроизводимый replay.

## Что сделать

Добавь:

- seed партии;
- список действий;
- список событий;
- начальную конфигурацию;
- финальный результат;
- причину окончания игры;
- версию/коммит, если можно получить;
- coverage summary на момент партии.

Команда:

```bash
python -m src.game.simulate --players 3 --games 1 --seed 100 --replay-dir data/replays
```

Формат:

```text
data/replays/game_<seed>_<timestamp>.json
```

Replay должен содержать достаточно данных, чтобы понять:

- кто ходил;
- какие карты были в руке;
- какие действия выбрал агент;
- какие эффекты сработали;
- какие эффекты были пропущены;
- почему партия закончилась;
- кто победил.

Не обязательно реализовывать replay playback на этом этапе, но формат должен быть пригоден для будущего playback.

## Тесты

Добавь тесты:

- `test_replay_file_created`;
- `test_replay_contains_seed`;
- `test_replay_contains_actions_and_events`;
- `test_replay_contains_final_scores`.

---

# 10. Strict mode

## Цель

Должно быть два режима симуляции:

- `strict=False` — нереализованные эффекты логируются и игра продолжается;
- `strict=True` — нереализованный эффект вызывает понятную ошибку.

## Что сделать

Проверь и доведи strict mode во всех местах:

- эффекты карт;
- защиты;
- постоянки;
- групповые атаки;
- беспределы;
- scoring effects.

Добавь CLI-опцию:

```bash
python -m src.game.simulate --players 3 --games 1 --seed 100 --strict
```

## Тесты

Добавь тесты:

- `test_unimplemented_effect_logs_in_non_strict`;
- `test_unimplemented_effect_raises_in_strict`;
- `test_unimplemented_group_attack_raises_in_strict`;
- `test_unimplemented_mayhem_raises_in_strict`.

---

# 11. Обновить документацию

Обнови:

- `README.md`;
- `docs/decisions.md`;
- `docs/engine_architecture.md`.

Создай:

```text
docs/progress_stage_2_6.md
docs/effect_coverage.md
```

В `docs/progress_stage_2_6.md` укажи:

- что сделано;
- какие модули изменены;
- какие тесты добавлены;
- что стало ближе к правилам;
- какие эффекты всё ещё не реализованы;
- какие механики блокируют этап 3;
- рекомендации для этапа 2.7.

В `docs/decisions.md` зафиксируй:

- как выбран формат deck manifest;
- почему введён или не введён `CardInstance`;
- как устроено разделение текста на секции;
- как классифицируются статусы coverage.

---

# 12. Финальная проверка

Перед завершением обязательно запусти:

```bash
pytest
python -m src.game.simulate --players 2 --games 5 --seed 100
python -m src.game.simulate --players 3 --games 10 --seed 100
python -m src.game.simulate --players 5 --games 5 --seed 100
python -m src.game.effect_coverage
```

Если добавлен replay:

```bash
python -m src.game.simulate --players 3 --games 1 --seed 100 --replay-dir data/replays
```

Если добавлен strict mode:

```bash
python -m src.game.simulate --players 3 --games 1 --seed 100 --strict
```

`strict` может падать на нереализованных эффектах, но ошибка должна быть понятной и ожидаемой.

---

# Definition of Done

Этап 2.6 считается завершённым, если:

- `pytest` проходит;
- симуляции на 2, 3 и 5 игроков проходят без падений в `strict=False`;
- есть `deck_manifest.json` или эквивалентная система quantity;
- setup использует физические количества карт;
- стартовые колоды соответствуют правилам;
- шальная магия и вялые палочки имеют правильные размеры стопок;
- жетоны дохлых колдунов создаются как `player_count * 4`;
- Вум всегда первая открытая легенда;
- количество легенд зависит от числа игроков;
- фамильяр сначала лежит под планшетом, а после покупки уходит в сброс;
- защита фамильяра доступна только когда карта фамильяра находится на руке;
- введены `CardInstance` или эквивалентные однозначные ссылки на физические карты;
- текст карт разделяется на секции;
- защита не применяется при обычном розыгрыше;
- атака не применяется как простой main-text без attack resolver;
- coverage report стал честнее и полезнее;
- `Пшик` / `Вялая палочка` или аналогичные карты без эффекта не считаются ошибочно `not_implemented`;
- реализованы 20–30 ключевых карт или паттернов эффектов;
- replay/debug log создаётся по CLI-опции;
- документация обновлена;
- создан `docs/progress_stage_2_6.md`.

---

# Что НЕ делать на этапе 2.6

Не делай:

- RL;
- PettingZoo / Gymnasium;
- Stable-Baselines;
- FastAPI;
- React UI;
- мобильный интерфейс;
- сетевую игру;
- красивую визуализацию карт;
- массовый ручной переперенос карт;
- переписывание проекта с нуля.

После завершения этапа 2.6 проект должен быть готов к этапу 2.7: scripted-агенты, эвристики, replay-анализ и подготовка observation/action model для будущего RL.
