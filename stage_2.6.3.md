# Запрос для Codex-агента: Stage 2.6.3 — Pending Choices and Mayhem Completion Pass

Ты работаешь в существующем проекте цифрового симулятора настольной карточной игры **«Эпичные схватки боевых магов. Крутагидон»**.

Репозиторий: `https://github.com/Va-ler-ka/Krutogidon`
Основная ветка: `origin/main`
Текущий ориентир: после коммита `80071ec Implement stage 2.6.2 source-aware pipeline`.

## Контекст

Stage 2.6.2 был частично, но существенно закрыт.

Уже есть:

* `SourceKind` для damage/death pipeline;
* `EffectRequest`;
* `-3 VP` за жетоны дохлых колдунов;
* tie-breaker на меньшее число ЖДК;
* health cap 25;
* death reset к 20;
* `GameState.trophy_controller_id`;
* выдача Главного приза за player-card / player-mayhem kill;
* запрет выдачи Главного приза за self kill / legend group attack / market mayhem;
* group attack lifecycle: defense window не теряется при reveal легенды в конце хода;
* market/player mayhem damage через общий pipeline;
* coverage со статусами `partial_safe` / `partial_unsafe`;
* registry для `implemented_with_tests`;
* replay summary с source_kind, trophy, defense, redirect, mayhem/group/partial diagnostics;
* `pytest` проходил: 107 passed;
* `validate_manifest`, `effect_coverage`, симуляции 2/3/5 игроков и replay summary проходили.

Но Stage 2.6.2 ещё не идеален.

Известные ограничения:

* `strict=True` ожидаемо падает на `беспредел_10`: сложный market mayhem эффект «Разыграй каждую атаку на картах с барахолки»;
* trophy discard в конце хода пока временно auto-discard;
* нет полноценного pending choice для destroy/discard/gain;
* часть mayhem pipeline ещё неполная;
* `partial_safe` пока почти не используется содержательно;
* replay остаётся summary/debug без playback;
* Stage 2.7 scripted agents ещё не начат и пока начинать его рано.

## Главная задача Stage 2.6.3

Не переходи к агентам, RL, Gymnasium, PettingZoo, FastAPI, UI или мобильной версии.

Цель Stage 2.6.3 — закрыть оставшиеся блокеры Stage 2.6.2:

1. ввести полноценный pending-choice pipeline для стратегических выборов;
2. заменить временный trophy auto-discard на pending choice;
3. реализовать или корректно разложить `беспредел_10`;
4. усилить mayhem pipeline;
5. снизить количество `not_implemented` / `partial_unsafe` за счёт безопасных rule-correct реализаций;
6. улучшить replay diagnostics;
7. подготовить движок к последующим проходам по постоянкам, фамильярам и эффектам карт.

Если объём слишком большой, приоритет такой:

```text
1. pending choice framework;
2. trophy discard pending choice;
3. беспредел_10;
4. mayhem attack/choice pipeline;
5. destroy/discard/gain pending choices;
6. coverage/replay/docs.
```

---

# Жёсткие ограничения

Не делай:

* scripted agents;
* RL;
* Gymnasium;
* PettingZoo;
* Stable-Baselines;
* FastAPI;
* React UI;
* мобильный интерфейс;
* сетевую игру;
* replay playback;
* переписывание проекта с нуля.

Не добавляй ложные реализации. Лучше честный `partial_unsafe` / `not_implemented`, чем silent-wrong поведение.

Все новые механики должны быть:

* детерминируемыми при seed;
* совместимыми с replay/debug log;
* покрыты тестами;
* отражены в `effect_coverage`;
* документированы.

---

# Перед началом

Обнови репозиторий:

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
docs/effect_coverage.md
docs/plan_stage_2_6_2.md
docs/progress_stage_2_6_2.md
data/processed/cards_full.json
data/processed/deck_manifest.json
data/processed/effect_coverage.json
src/game/models.py
src/game/engine.py
src/game/effects.py
src/game/mayhem.py
src/game/legal_actions.py
src/game/replay_summary.py
src/game/effect_coverage.py
src/game/implemented_patterns.py
tests/*
```

Создай план:

```text
docs/plan_stage_2_6_3.md
```

В плане укажи:

* текущее состояние;
* подтверждённые проблемы;
* какие модули будешь менять;
* какие тесты добавишь;
* какие риски есть;
* что не входит в Stage 2.6.3.

Не начинай крупные изменения, пока не создан `docs/plan_stage_2_6_3.md`.

---

# 1. Baseline перед изменениями

Запусти и зафиксируй в плане:

```bash
pytest
python -m src.game.validate_manifest
python -m src.game.effect_coverage
python -m src.game.simulate --players 2 --games 5 --seed 100
python -m src.game.simulate --players 3 --games 10 --seed 100
python -m src.game.simulate --players 5 --games 5 --seed 100
python -m src.game.simulate --players 3 --games 1 --seed 100 --replay-dir data/replays
python -m src.game.replay_summary data/replays/<latest>.json
python -m src.game.simulate --players 3 --games 1 --seed 100 --strict
```

Ожидаемо, strict может падать на `беспредел_10`. Если падает на другом эффекте, зафиксируй это.

---

# 2. Ввести полноценный PendingChoice pipeline

## Проблема

Сейчас часть выборов может выполняться автоматически:

* trophy discard;
* destroy from hand/discard;
* discard choice;
* gain from market;
* mayhem choices;
* некоторые target/tie choices.

Это плохо для будущих агентов и для верности игре.

## Что сделать

Проверь существующий `pending_choice`. Если он уже есть, расширь его. Если нет, введи универсальную модель:

```python
class PendingChoiceType(str, Enum):
    CHOOSE_TARGET = "choose_target"
    USE_OR_DECLINE_DEFENSE = "use_or_decline_defense"
    DISCARD_CARD = "discard_card"
    DESTROY_CARD = "destroy_card"
    GAIN_CARD = "gain_card"
    MAYHEM_CHOICE = "mayhem_choice"
    TROPHY_DISCARD = "trophy_discard"
    CHOOSE_MARKET_ATTACK_TARGET = "choose_market_attack_target"
    CHOOSE_CARD_TO_PLAY_FROM_MARKET = "choose_card_to_play_from_market"

@dataclass
class PendingChoice:
    choice_id: str
    choice_type: PendingChoiceType
    player_id: int
    source_kind: SourceKind | None
    source_card_id: str | None
    source_card_instance_id: str | None
    options: list[dict]
    min_choices: int = 1
    max_choices: int = 1
    metadata: dict[str, Any] = field(default_factory=dict)
```

Требования:

* `GameState` хранит текущий pending choice или очередь pending choices;
* `LegalActionGenerator` строит legal actions из pending choice;
* `apply_action` умеет resolve pending choice;
* `RandomAgent` выбирает случайный legal option;
* replay логирует:

  * pending choice created;
  * options count;
  * selected option;
  * source_kind;
  * source_card_id;
  * result.

## Тесты

Добавь тесты:

```text
test_pending_choice_serializes
test_legal_actions_generated_from_pending_choice
test_random_agent_resolves_pending_choice
test_pending_choice_resolution_logged
test_illegal_pending_choice_option_rejected
```

---

# 3. Trophy discard через pending choice

## Проблема

В Stage 2.6.2 контроллер Главного приза в конце хода добирает до 6 и временно auto-discards одну карту.

Нужно заменить это на rule-correct pending choice.

## Правило

Пока игрок контролирует Главный приз, в конце своего хода он:

```text
берёт 6 карт;
сбрасывает 1 карту.
```

## Что сделать

* в конце хода, если `active_player_id == trophy_controller_id`, игрок добирает нужные карты;
* затем создаётся `PendingChoiceType.TROPHY_DISCARD`;
* legal actions предлагают все карты на руке этого игрока;
* выбранная карта уходит в сброс;
* после resolve хода продолжается обычный end-turn flow;
* auto-discard убрать из production-кода;
* если нужен helper для тестов, вынести в тестовый helper и явно назвать.

## Тесты

Добавь тесты:

```text
test_trophy_end_turn_creates_discard_pending_choice
test_trophy_discard_legal_actions_are_hand_cards
test_trophy_discard_moves_selected_card_to_discard
test_trophy_discard_continues_end_turn_after_resolution
test_trophy_discard_recorded_in_replay
test_no_auto_discard_for_trophy_in_production_flow
```

---

# 4. Реализовать `беспредел_10`: «Разыграй каждую атаку на картах с барахолки»

## Контекст

Сейчас strict падает на `беспредел_10`, текст: «Разыграй каждую атаку на картах с барахолки».

Это важный блокер strict-mode.

## Правило для цифровой реализации

Когда `беспредел_10` выходит на барахолку во время игрового пополнения рынка:

1. он не занимает слот рынка;
2. создаётся market mayhem request;
3. движок находит все открытые карты на барахолке, у которых есть attack section / attack flag;
4. для каждой такой карты разыгрывается только её attack section;
5. не-attack main text этих карт не применяется;
6. source_kind остаётся `MARKET_MAYHEM`;
7. source_player_id отсутствует;
8. Главный приз за смерти от этих атак не выдаётся;
9. защита разрешена, если атака позволяет защиту;
10. familiar redirect против этих атак не должен наносить урон несуществующему атакующему;
11. если атака требует выбора цели, выбор делает текущий активный игрок через pending choice, но source всё равно остаётся `MARKET_MAYHEM`;
12. атаки разрешаются в порядке карт на барахолке слева направо / по порядку списка market;
13. если атака карты слишком сложная, она логируется как `partial_unsafe`; в strict-mode это должно падать понятной ошибкой с указанием карты рынка и беспредела.

## Что сделать

Добавь mayhem handler для `беспредел_10`.

Не делай огромный `if title == ...` в core engine. Допустимо:

* registry для специальных mayhem handlers;
* `mayhem_id -> handler`;
* handler использует primitives и общий attack pipeline.

Пример архитектуры:

```python
MAYHEM_HANDLERS = {
    "беспредел_10": PlayEachMarketAttackHandler(),
}
```

или эквивалент.

## Тесты

Добавь тесты:

```text
test_bespredel_10_detects_attack_cards_in_market
test_bespredel_10_plays_only_attack_sections
test_bespredel_10_does_not_apply_main_text
test_bespredel_10_uses_market_mayhem_source_kind
test_bespredel_10_death_does_not_award_trophy
test_bespredel_10_allows_defense
test_bespredel_10_familiar_redirect_has_no_attacker
test_bespredel_10_target_choice_uses_pending_choice
test_bespredel_10_strict_fails_on_unparseable_market_attack
test_bespredel_10_non_strict_logs_partial_unsafe_for_unparseable_market_attack
```

---

# 5. Улучшить общий mayhem pipeline

## Текущее состояние

Stage 2.6.2 уже провёл market/player mayhem damage через общий source-aware pipeline, но часть mayhem осталась `not_implemented`.

## Важно: initial market setup

Не ломай правило начального рынка:

```text
беспределы в изначальном ассортименте НЕ разыгрываются;
они отправляются в destroyed/mayhem discard pile и заменяются;
стартовая барахолка должна состоять из 5 карт без беспредела.
```

## Gameplay market fill

Во время игры, когда беспредел выходит при пополнении рынка:

```text
- заполнение рынка временно приостанавливается;
- беспредел разрешается через mayhem pipeline;
- затем уходит в mayhem discard / destroyed mayhem pile;
- затем рынок продолжает пополняться до 5;
- если колоды не хватает, отмечается условие конца игры.
```

## Минимальные mayhem-паттерны для Stage 2.6.3

Реализуй или улучши:

```text
1. каждый колдун получает N урона;
2. каждый враг / каждый колдун получает вялую палочку;
3. каждый колдун сбрасывает N карт;
4. каждый колдун может выбрать A или B;
5. примени групповую атаку текущей легенды;
6. разыграй каждую атаку на картах с барахолки.
```

Для всех остальных:

* `strict=False`: логировать `partial_unsafe` или `not_implemented`;
* `strict=True`: падать понятной ошибкой;
* не применять ложный частичный эффект, если он может исказить игру.

## Тесты

Добавь тесты:

```text
test_initial_market_mayhem_not_resolved
test_gameplay_market_mayhem_resolved_and_replaced
test_market_refills_to_five_after_mayhem
test_market_mayhem_each_wizard_damage
test_market_mayhem_each_wizard_weak_wand
test_market_mayhem_each_wizard_discard_pending_choice
test_market_mayhem_choice_creates_pending_choice
test_market_mayhem_apply_current_legend_group_attack
test_market_mayhem_unknown_strict_raises
test_market_mayhem_unknown_non_strict_logs
```

---

# 6. Pending choices для destroy/discard/gain

## Что сделать

Переведи следующие эффекты с auto-choice на pending choice:

```text
DestroyCard
DiscardCards
GainCard
```

Минимальные правила:

* если эффект говорит «уничтожь карту с руки» — pending choice по картам руки;
* если эффект говорит «уничтожь карту из сброса» — pending choice по картам сброса;
* если эффект говорит «уничтожь карту со своей руки или из сброса» — options включают обе зоны;
* если эффект говорит «сбрось карту» — pending choice по руке;
* если эффект говорит «получи карту с барахолки» — pending choice по доступным картам рынка;
* если выбор невозможен, эффект логирует no-op reason, но не падает в non-strict;
* если strict и эффект требует невозможного выбора из-за неполной реализации, ошибка должна быть понятной.

## Тесты

Добавь тесты:

```text
test_destroy_from_hand_creates_pending_choice
test_destroy_from_discard_creates_pending_choice
test_destroy_from_hand_or_discard_options_include_zones
test_discard_card_creates_pending_choice
test_gain_card_from_market_creates_pending_choice
test_pending_destroy_removes_selected_instance
test_pending_discard_moves_selected_instance_to_discard
test_pending_gain_moves_selected_market_instance_to_discard
test_random_agent_handles_destroy_discard_gain_choices
```

---

# 7. Defense/redirect regression pass

Stage 2.6.2 уже добавил нейтральный источник для group attack / market mayhem. Теперь нужно убедиться, что это не ломается в новых mayhem handlers.

Требования:

* защита доступна против player attack;
* защита доступна против group attack;
* защита доступна против market mayhem attack;
* защита защищает только защищающегося игрока;
* familiar redirect работает только если `redirectable=True` и есть `source_player_id`;
* familiar redirect против `MARKET_MAYHEM` и `LEGEND_GROUP_ATTACK` логирует ignored redirect и не наносит урон предыдущему игроку;
* атакующий не может защищаться от redirect;
* redirect использует уже вычисленный урон, а не пересчитывает его.

## Тесты

Добавь или проверь тесты:

```text
test_defense_against_player_attack
test_defense_against_group_attack
test_defense_against_market_mayhem_attack
test_familiar_redirect_player_attack
test_familiar_redirect_ignored_for_market_mayhem
test_familiar_redirect_ignored_for_legend_group_attack
test_attacker_cannot_defend_against_redirect
test_redirect_uses_original_damage_amount
```

---

# 8. Coverage: сделать partial_safe осмысленным

Сейчас `partial_safe` фактически не используется, а большинство частичных эффектов — `partial_unsafe`.

## Что сделать

Не нужно искусственно повышать coverage.

Нужно:

* оставить `partial_unsafe` для всех state-changing неполных эффектов;
* ввести `partial_safe` только для реально безопасных случаев;
* добавить в coverage report объяснение, почему карта получила `partial_safe` или `partial_unsafe`;
* добавить top missing mechanics;
* добавить список mayhem blockers;
* после реализации `беспредел_10` он не должен быть `not_implemented`.

## Тесты

Добавь тесты:

```text
test_partial_safe_requires_reason
test_partial_unsafe_requires_missing_mechanic
test_bespredel_10_no_longer_not_implemented_after_handler
test_coverage_reports_mayhem_blockers
test_coverage_reports_pending_choice_blockers
```

---

# 9. Replay summary: усилить диагностику choices/mayhem

`replay_summary` уже показывает source_kind, trophy, defenses, mayhem/group/partial diagnostics. Нужно добавить pending choice counters.

Добавь:

```text
pending_choices_created_count
pending_choices_resolved_count
pending_choices_by_type
auto_choices_count
mayhem_handlers_used
mayhem_unimplemented_count
mayhem_partial_unsafe_count
trophy_discard_choices_count
destroy_discard_gain_choices_count
```

Требование:

* после Stage 2.6.3 в production flow не должно быть auto-choice для trophy discard;
* если auto-choice ещё где-то остался, replay_summary должен явно показать его.

## Тесты

Добавь тесты:

```text
test_replay_summary_counts_pending_choices
test_replay_summary_counts_pending_choice_types
test_replay_summary_counts_auto_choices
test_replay_summary_reports_mayhem_handlers_used
test_replay_summary_reports_trophy_discard_choice
```

---

# 10. Документация

Создай:

```text
docs/plan_stage_2_6_3.md
docs/progress_stage_2_6_3.md
```

Обнови:

```text
README.md
docs/decisions.md
docs/engine_architecture.md
docs/effect_coverage.md
```

В `docs/progress_stage_2_6_3.md` укажи:

```text
- что было исправлено;
- закрыт ли беспредел_10;
- какие pending choices реализованы;
- остались ли auto-choice в production flow;
- падает ли strict и на какой карте/механике;
- сколько implemented_with_tests / partial_safe / partial_unsafe / not_implemented;
- какие команды реально прогнаны;
- можно ли считать Stage 2.6.2 DoD полностью закрытым;
- что остаётся для Stage 2.6.4.
```

---

# Финальные проверки

Запусти:

```bash
pytest
python -m src.game.validate_manifest
python -m src.game.effect_coverage
python -m src.game.simulate --players 2 --games 5 --seed 100
python -m src.game.simulate --players 3 --games 10 --seed 100
python -m src.game.simulate --players 5 --games 5 --seed 100
python -m src.game.simulate --players 3 --games 1 --seed 100 --replay-dir data/replays
python -m src.game.replay_summary data/replays/<latest>.json
python -m src.game.simulate --players 3 --games 1 --seed 100 --strict
```

Если `strict` всё ещё падает, это допустимо, но только если:

```text
- он больше не падает на беспредел_10;
- он падает на явно известный partial_unsafe/not_implemented эффект;
- docs/progress_stage_2_6_3.md указывает карту, эффект, source_kind и следующий этап для закрытия.
```

---

# Definition of Done Stage 2.6.3

Stage 2.6.3 считается завершённым, если:

```text
pytest проходит;
validate_manifest проходит;
effect_coverage проходит;
симуляции 2/3/5 игроков проходят в strict=False;
trophy discard больше не auto-discard в production flow;
trophy discard использует pending choice;
DestroyCard / DiscardCards / GainCard используют pending choice там, где нужен выбор;
RandomAgent умеет разрешать новые pending choices;
беспредел_10 реализован или разложен через корректный handler;
беспредел_10 больше не является not_implemented;
market mayhem attacks используют source_kind MARKET_MAYHEM;
смерти от market mayhem не выдают Главный приз;
защита против market mayhem работает;
familiar redirect против market mayhem / legend group attack не наносит урон несуществующему атакующему;
replay_summary показывает pending choices и mayhem handlers;
coverage показывает mayhem blockers и pending-choice blockers;
docs/progress_stage_2_6_3.md создан.
```

---

# Что НЕ делать

Не начинать Stage 2.7 scripted agents, пока не закрыты:

```text
- trophy pending discard;
- destroy/discard/gain pending choices;
- беспредел_10;
- mayhem attack defense;
- replay diagnostics for choices.
```

После Stage 2.6.3 следующий логичный этап:

```text
Stage 2.6.4 — Ongoing Triggers, Familiar Setup and More Card Effect Batches
```

А Stage 2.7 scripted agents стоит начинать только после нескольких таких 2.6.x проходов, когда strict падает только на редких уникальных картах, а не на базовых системных механиках.
