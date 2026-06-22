# Запрос для Codex-агента: Stage 2.6.1 — Fidelity Fixes and Engine Cleanup

Ты работаешь в существующем проекте симулятора настольной карточной игры **«Эпичные схватки боевых магов. Крутагидон»**.

Репозиторий: `https://github.com/Va-ler-ka/Krutogidon`
Основная ветка: `origin/main`
Текущий ориентир: после коммита `0771608 Implement stage 2.6 rule fidelity layer`

## Контекст

Этап 2.6 уже реализован и запушен. В проекте уже есть:

* `deck_manifest.json`;
* `CardInstance` / физические копии карт;
* секции текста карт;
* улучшенный `effect_coverage`;
* replay/debug log;
* strict mode;
* корректировка фамильяров;
* Вум как первая легенда;
* базовая работа с manifest;
* тесты и симуляции проходят в `strict=False`.

Но после ревью найдены важные расхождения и места, которые нужно стабилизировать перед этапом 2.7.

## Главная задача

Не переходи к RL, Gymnasium, PettingZoo, FastAPI, UI или мобильной версии.

Цель этапа 2.6.1 — исправить rule-fidelity ошибки, очистить архитектурные противоречия и подготовить движок к scripted-агентам.

Фокус:

1. правильный состав основной колоды по точным правилам тиражей;
2. исправление групповых атак легенд;
3. полная реализация стартовых карт, особенно `Палочка`;
4. очистка `GameConfig` от конфликтов с manifest;
5. расширение targeting parser;
6. перевод первых карт из `partial` в `implemented_with_tests`;
7. consistency pass по документации;
8. replay summarizer для анализа партий;
9. тесты на все исправления.

---

# 0. Перед началом

Сначала обнови локальный репозиторий:

```bash
git fetch origin
git checkout main
git pull origin main
```

Изучи:

```text
README.md
docs/decisions.md
docs/engine_architecture.md
docs/progress_stage_2_6.md
docs/effect_coverage.md
data/processed/cards_full.json
data/processed/deck_manifest.json
data/processed/effect_coverage.json
src/game/*
src/agents/*
tests/*
```

После анализа создай документ:

```text
docs/plan_stage_2_6_1.md
```

В нём опиши:

* текущее состояние;
* найденные проблемы;
* какие модули будешь менять;
* какие тесты добавишь;
* что не входит в этап 2.6.1;
* риски.

Не приступай к массовым изменениям, пока не создан `docs/plan_stage_2_6_1.md`.

---

# 1. Исправить состав основной колоды

## Важное уточнение по реальному составу основной колоды

Основная колода должна содержать **124 физические карты**.

Правило тиражей:

```text
1. Все карты Беспредела идут в 1 экземпляре.
   Всего: 26 карт.

2. Все карты со стоимостью 6 или 7, а также все карты типа Место идут в 1 экземпляре.
   Всего таких singleton-карт основной колоды без Беспредела: 18 карт.

3. Все остальные карты основной колоды идут в 2 экземплярах.
   Всего таких уникальных карт: 40.
   Физических карт: 40 * 2 = 80.

Итого:
26 + 18 + 80 = 124 карты.
```

## Что сделать

Обнови `data/processed/deck_manifest.json` или генератор manifest так, чтобы он строил основную колоду по этому правилу.

Логика должна быть не ручной по названиям карт, а по данным карты:

```text
if card.type == "Беспредел":
    quantity = 1
elif card.type == "Место":
    quantity = 1
elif card.cost in {6, 7}:
    quantity = 1
else:
    quantity = 2
```

Эта логика применяется только к картам основной колоды. Не включай сюда:

* стартовые карты;
* легенды;
* шальную магию;
* вялые палочки;
* фамильяров;
* жетоны;
* свойства;
* неигровые записи.

## Валидация

Добавь строгую валидацию manifest:

```text
main_deck_physical_count == 124
mayhem_unique_count == 26
singleton_non_mayhem_count == 18
double_unique_count == 40
double_physical_count == 80
```

Если эти числа не сходятся, команда setup/validation должна выдавать понятную ошибку с отчётом:

```text
- какие карты попали в singleton;
- какие карты попали в double;
- какие карты попали в mayhem;
- какие карты не попали никуда;
- какие карты попали в неправильную группу.
```

## Команда

Добавь или обнови команду:

```bash
python -m src.game.validate_manifest
```

Она должна печатать summary и завершаться с кодом ошибки, если manifest некорректен.

## Тесты

Добавь тесты:

```text
test_manifest_main_deck_total_is_124
test_manifest_mayhem_count_is_26
test_manifest_singleton_non_mayhem_count_is_18
test_manifest_double_unique_count_is_40
test_manifest_double_physical_count_is_80
test_cost_6_and_7_cards_are_singletons
test_places_are_singletons
test_non_special_main_deck_cards_are_doubles
test_manifest_validation_reports_mismatch
```

---

# 2. Исправить групповые атаки легенд

## Проблема

Групповая атака легенды должна применяться **к каждому колдуну**, а не только к врагам активного игрока.

## Что сделать

Проверь `resolve_group_attack` или аналогичный код.

Для групповой атаки легенды:

```text
targets = all players / all wizards
```

Не используй `all_enemies` для групповой атаки легенды.

Порядок применения:

```text
начиная с колдуна, чей ход будет следующим
далее по часовой стрелке
```

## Требования

* Каждый колдун получает возможность защититься, если у него есть карта защиты.
* Групповая атака не считается ходом конкретного игрока.
* Групповая атака не должна случайно исключать игрока, победившего предыдущую легенду.
* Если эффект групповой атаки не реализован, он логируется в `strict=False`.
* В `strict=True` нереализованная групповая атака должна падать понятной ошибкой.

## Тесты

Добавь тесты:

```text
test_legend_group_attack_targets_all_wizards
test_legend_group_attack_starts_from_next_player
test_legend_group_attack_allows_each_wizard_to_defend
test_legend_group_attack_does_not_exclude_previous_actor
test_unimplemented_group_attack_raises_in_strict
```

---

# 3. Полностью реализовать стартовые карты

## Цель

Стартовые карты должны быть полностью реализованы и не должны валить `strict mode`.

Обязательные карты:

```text
Знак
Пшик
Палочка
```

Если в проекте есть ещё стартовые карты, проверь их тоже.

## Правила

`Знак`:

```text
+1 мощь
```

`Пшик`:

```text
эффекта нет
```

`Палочка`:

```text
+1 мощь
Атака: нанеси 1 урон выбранному колдуну.
Если он от этого подох, возьми 2 карты.
```

## Что сделать

* Переведи эти карты в `implemented_with_tests`.
* `Пшик` должен классифицироваться как `no_effect`, а не `not_implemented`.
* `Палочка` должна работать в `strict=True`.
* Урон от `Палочки` должен проходить через обычный attack resolver.
* Цель атаки должна выбираться легальным действием.
* Условный добор 2 карт должен срабатывать только если цель умерла именно от этой атаки.

## Тесты

Добавь тесты:

```text
test_sign_gives_one_power
test_pshik_has_no_effect
test_wand_gives_one_power
test_wand_attack_deals_one_damage_to_chosen_wizard
test_wand_attack_can_be_defended
test_wand_draws_two_if_attack_kills_target
test_wand_does_not_draw_if_target_survives
test_starter_cards_do_not_fail_in_strict_mode
```

---

# 4. Очистить GameConfig от конфликтов с manifest

## Проблема

В `GameConfig` могут оставаться старые поля вроде:

```text
weak_wand_count = 40
wild_magic_count = 40
dead_wizard_token_limit = 20
```

Но после stage 2.6 эти значения должны определяться через manifest и правила:

```text
wild_magic = 16
weak_wands = 16
dead_wizard_tokens = player_count * 4
```

## Что сделать

Проверь `GameConfig`.

Возможные решения:

1. удалить устаревшие поля;
2. оставить их только как override для тестов;
3. явно пометить deprecated;
4. гарантировать, что setup не использует старые значения, если есть manifest.

## Требования

* В обычной игре значения берутся из manifest/rules.
* Старые дефолты не должны влиять на setup.
* Если override оставлен для тестов, он должен быть явно назван, например:

```text
override_weak_wand_count
override_wild_magic_count
override_dead_wizard_token_count
```

## Тесты

Добавь тесты:

```text
test_setup_uses_manifest_wild_magic_count
test_setup_uses_manifest_weak_wand_count
test_dead_wizard_tokens_are_player_count_times_four
test_game_config_deprecated_counts_do_not_override_manifest
```

---

# 5. Расширить targeting parser

## Проблема

Сейчас targeting parser может слишком грубо определять цели, например только:

```text
chosen_enemy
all_enemies
```

Нужно использовать уже заложенные selectors.

## Что сделать

Расширь парсер эффектов и/или секций атаки, чтобы он распознавал:

```text
выбранному врагу
выбранному колдуну
каждому врагу
каждому колдуну
правому или левому врагу
левому врагу
правому врагу
самому хилому врагу
самому могучему врагу
врагам хилее тебя
врагам могучее тебя
колдуну/колдунам с минимумом
колдуну/колдунам с максимумом
```

## Требования

* `левый/правый враг` в игре на 2 игроков не должен дублировать эффект дважды.
* `самый хилый/самый могучий` при ничьей должен создавать `pending choice`.
* `каждому колдуну` должно включать самого игрока.
* `каждому врагу` должно исключать самого игрока.
* group attack легенды использует `каждому колдуну`, а не `каждому врагу`.

## Тесты

Добавь тесты:

```text
test_parse_chosen_enemy_selector
test_parse_chosen_wizard_selector
test_parse_each_enemy_selector
test_parse_each_wizard_selector
test_parse_left_or_right_enemy_selector
test_parse_left_right_two_player_no_duplicate
test_parse_weakest_enemy_selector
test_parse_strongest_enemy_selector
test_weakest_tie_creates_pending_choice
test_strongest_tie_creates_pending_choice
test_each_wizard_includes_self
test_each_enemy_excludes_self
```

---

# 6. Поднять coverage за счёт implemented_with_tests

## Цель

Не нужно реализовывать все карты. Нужно перевести первые важные карты и паттерны из `partial` в `implemented_with_tests`.

Минимальная цель этапа:

```text
implemented_with_tests >= 12
not_implemented <= текущее значение
no_effect корректно классифицирует карты без эффекта
```

Приоритет:

1. стартовые карты;
2. шальная магия;
3. вялая палочка;
4. простые карты с `+N мощи`;
5. простые карты с `Возьми N карт`;
6. простые атаки на выбранного врага;
7. простые атаки на каждого врага;
8. простые защиты;
9. 2–3 простых групповых атаки легенд;
10. 2–3 простых беспредела.

## Требования

* Не делай огромный `if/else` по названиям карт.
* Используй primitive effects.
* Для уникальных карт допускается `effect_id`, но эффект должен быть собран из primitives.
* Coverage должен показывать, почему карта получила конкретный статус.

## Тесты

Добавь тесты на новые fully implemented карты/паттерны.

Минимально:

```text
test_wild_magic_basic_power_option
test_weak_wand_no_effect_and_negative_vp_if_supported
test_simple_draw_card_implemented_with_tests
test_simple_damage_attack_implemented_with_tests
test_simple_defense_implemented_with_tests
test_simple_group_attack_implemented_with_tests
test_simple_mayhem_implemented_with_tests
```

---

# 7. Replay summarizer

## Цель

Replay уже создаётся. Теперь нужен простой инструмент анализа replay, чтобы понимать, насколько партия была полноценной.

## Что сделать

Добавь команду:

```bash
python -m src.game.replay_summary data/replays/<file>.json
```

Она должна выводить:

```text
seed
players
winner
turn_count
end_reason
final_scores
cards_played_count
cards_bought_count
attacks_resolved_count
defenses_used_count
deaths_count
mayhems_revealed_count
legends_defeated_count
unimplemented_effects_count
partial_effects_count
top_unimplemented_cards
top_partial_cards
```

Если файл не найден или формат неверный — понятная ошибка.

## Тесты

Добавь тесты:

```text
test_replay_summary_reads_replay
test_replay_summary_counts_unimplemented_effects
test_replay_summary_counts_partial_effects
test_replay_summary_reports_winner_and_end_reason
test_replay_summary_handles_missing_file
```

---

# 8. Documentation consistency pass

## Проблема

Некоторые документы могут описывать старое состояние: уникальные карты вместо manifest, stage 2.5 вместо stage 2.6, старые ограничения.

## Что сделать

Обнови:

```text
README.md
docs/decisions.md
docs/engine_architecture.md
docs/progress_stage_2_6.md
docs/effect_coverage.md
```

Создай:

```text
docs/progress_stage_2_6_1.md
```

В `docs/progress_stage_2_6_1.md` укажи:

```text
что исправлено
какие rule-fidelity ошибки закрыты
как теперь устроен manifest
какие тесты добавлены
сколько карт implemented_with_tests
что всё ещё partial / not_implemented
что остаётся перед stage 2.7
```

В `docs/decisions.md` зафиксируй:

```text
точное правило тиражей основной колоды:
- Беспределы x1;
- стоимость 6/7 x1;
- Места x1;
- остальные основные карты x2;
- итог 124 карты.
```

## Тесты / проверки документации

Добавь хотя бы простую проверку, если в проекте уже есть doc tests или markdown lint. Если нет — достаточно обновить документы вручную.

---

# 9. Финальные проверки

Перед завершением обязательно запусти:

```bash
pytest
python -m src.game.validate_manifest
python -m src.game.effect_coverage
python -m src.game.simulate --players 2 --games 5 --seed 100
python -m src.game.simulate --players 3 --games 10 --seed 100
python -m src.game.simulate --players 5 --games 5 --seed 100
python -m src.game.simulate --players 3 --games 1 --seed 100 --replay-dir data/replays
```

Проверь strict mode:

```bash
python -m src.game.simulate --players 3 --games 1 --seed 100 --strict
```

Если strict всё ещё падает, это допустимо только на реально сложной не реализованной карте.
Strict **не должен падать** на стартовых картах:

```text
Знак
Пшик
Палочка
```

---

# Definition of Done

Этап 2.6.1 считается завершённым, если:

* `pytest` проходит;
* `python -m src.game.validate_manifest` проходит;
* основная колода содержит 124 физические карты;
* в manifest:

  * 26 Беспределов x1;
  * 18 singleton-карт основной колоды без Беспределов;
  * 40 double-карт основной колоды x2;
* стартовые колоды соответствуют правилам;
* шальная магия = 16 карт;
* вялые палочки = 16 карт;
* жетоны дохлых колдунов = `player_count * 4`;
* групповая атака легенды применяется ко всем колдунам;
* порядок групповой атаки начинается со следующего игрока;
* `Знак`, `Пшик`, `Палочка` полностью реализованы;
* strict mode не падает на стартовых картах;
* `Палочка` наносит 1 урон через attack resolver;
* `Палочка` добирает 2 карты только если убила цель;
* `GameConfig` не конфликтует с manifest;
* targeting parser распознаёт left/right, weakest/strongest, each enemy, each wizard;
* `implemented_with_tests >= 12`;
* replay summarizer работает;
* документация обновлена;
* создан `docs/progress_stage_2_6_1.md`.

---

# Что НЕ делать

Не делай:

* RL;
* Gymnasium;
* PettingZoo;
* Stable-Baselines;
* FastAPI;
* React UI;
* мобильный интерфейс;
* красивую графику;
* сетевую игру;
* переписывание проекта с нуля.

После завершения 2.6.1 проект должен быть готов к **Stage 2.7 — Scripted Agents and Evaluation**.
