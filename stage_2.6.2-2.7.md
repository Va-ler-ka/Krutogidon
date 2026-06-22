# Запрос для Codex-агента: Stage 2.6.2 / 2.7 — Rule-Correct Event Pipeline and Scripted Agents Prep

Ты работаешь в существующем проекте цифрового симулятора настольной карточной игры **«Эпичные схватки боевых магов. Крутагидон»**.

Основная ветка: `origin/main`
Текущий ориентир: состояние после Stage 2.6.1, включая коммит `080ff3f Implement stage 2.6.1 rule fidelity checks`, если он есть в истории.

## Цель итерации

Эта итерация состоит из двух последовательных частей:

1. **Stage 2.6.2 — Bugfix and Rule-Correct Event Pipeline**

   * исправить критические rule-fidelity ошибки;
   * стабилизировать damage/death/defense/mayhem/group-attack pipeline;
   * улучшить strict-mode и replay/debug;
   * закрыть блокеры перед scripted-агентами.

2. **Stage 2.7 — Scripted Agents and Evaluation Prep**

   * начинать только после полного прохождения Definition of Done для Stage 2.6.2;
   * добавить scripted-агентов и evaluation-команды;
   * не делать RL, Gymnasium, PettingZoo, FastAPI, UI или мобильную версию.

Если объём слишком большой, **сделай только Stage 2.6.2 полностью** и явно зафиксируй в `docs/progress_stage_2_6_2.md`, что Stage 2.7 не начат.

---

# Жёсткие ограничения

Не делай:

* RL;
* Gymnasium;
* PettingZoo;
* Stable-Baselines;
* FastAPI;
* React UI;
* мобильный интерфейс;
* сетевую игру;
* красивую визуализацию;
* переписывание движка с нуля.

Не подменяй неизвестные эффекты догадками. Если эффект карты не реализован полностью, он должен явно попадать в `partial`, `partial_safe`, `partial_unsafe` или `not_implemented`, а `strict=True` должен это обнаруживать.

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
docs/progress_stage_2_6_1.md
data/processed/cards_full.json
data/processed/deck_manifest.json
data/processed/effect_coverage.json
src/game/*
src/agents/*
tests/*
```

Создай план:

```text
docs/plan_stage_2_6_2.md
```

В плане укажи:

* текущее состояние;
* какие проблемы подтверждены кодом;
* какие модули будешь менять;
* какие тесты добавишь;
* какие риски есть;
* что не входит в Stage 2.6.2.

Не приступай к крупным изменениям, пока не создан `docs/plan_stage_2_6_2.md`.

---

# Stage 2.6.2 — Bugfix and Rule-Correct Event Pipeline

## 1. Smoke baseline перед изменениями

Сначала запусти текущие проверки, чтобы зафиксировать baseline:

```bash
pytest
python -m src.game.validate_manifest
python -m src.game.effect_coverage
python -m src.game.simulate --players 2 --games 5 --seed 100
python -m src.game.simulate --players 3 --games 10 --seed 100
python -m src.game.simulate --players 5 --games 5 --seed 100
python -m src.game.simulate --players 3 --games 1 --seed 100 --replay-dir data/replays
```

Если что-то падает до изменений, зафиксируй это в `docs/plan_stage_2_6_2.md`.

---

## 2. Исправить scoring, health cap и death reset

### 2.1. Жетоны дохлых колдунов

Правило:

```text
каждый жетон дохлого колдуна = -3 VP в конце игры
tie-breaker: при равных VP меньше ЖДК лучше
```

Проверь и исправь:

```text
src/game/scoring.py
```

Тесты:

```text
test_dead_wizard_token_penalty_zero
test_dead_wizard_token_penalty_one_is_minus_three
test_dead_wizard_token_penalty_two_is_minus_six
test_dead_wizard_token_tiebreaker_fewer_tokens_wins
```

### 2.2. Максимум жизней

Правило:

```text
максимум жизней = 25
лечение выше 25 не поднимает
```

Добавь или проверь:

```python
GameConfig.max_health = 25
```

`Heal` и любые другие healing-эффекты должны использовать:

```python
min(config.max_health, player.health + amount)
```

Тесты:

```text
test_heal_under_cap
test_heal_to_cap
test_heal_does_not_exceed_25
```

### 2.3. Смерть и воскрешение

Правило:

```text
когда здоровье ниже 1, игрок получает случайный ЖДК и снова становится 20 жизней,
если сам ЖДК не говорит иного
```

Убери `TODO_RULE_CLARIFICATION` для базового reset health.

Требования:

* `GameConfig.death_reset_health = 20`;
* смерть логируется;
* получение ЖДК логируется;
* если закончилась стопка ЖДК, игра заканчивается в конце текущего хода;
* будущие особые ЖДК должны иметь точку расширения, но сейчас их можно оставить `not_implemented`.

Тесты:

```text
test_death_gives_dead_wizard_token
test_death_resets_health_to_20
test_death_token_stack_empty_sets_game_end_pending
test_death_event_logged
```

---

## 3. Ввести единый DamageRequest / EffectRequest

Сейчас урон, смерти, защиты, групповые атаки и беспределы могут обрабатываться разными путями. Нужно унифицировать источник эффекта.

Добавь или доработай модели:

```python
class SourceKind(str, Enum):
    PLAYER_CARD = "player_card"
    PLAYER_MAYHEM = "player_mayhem"
    MARKET_MAYHEM = "market_mayhem"
    LEGEND_GROUP_ATTACK = "legend_group_attack"
    DEAD_WIZARD_TOKEN = "dead_wizard_token"
    SELF = "self"
    SYSTEM = "system"

@dataclass
class EffectRequest:
    request_id: str
    source_kind: SourceKind
    source_player_id: int | None
    source_card_instance_id: str | None
    source_card_id: str | None
    targets: list[int]
    current_target_index: int = 0
    effects: list[Any] = field(default_factory=list)
    attack: bool = False
    defense_allowed: bool = False
    redirectable: bool = False
    already_redirected: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
```

Или используй эквивалентную структуру, если в проекте уже есть похожие модели.

Требования:

* обычные атаки игрока: `source_kind=PLAYER_CARD`, `source_player_id=<attacker>`, `defense_allowed=True`, `redirectable=True`;
* групповая атака легенды: `source_kind=LEGEND_GROUP_ATTACK`, `source_player_id=None`, `defense_allowed=True`, `redirectable=False`;
* беспредел с барахолки: `source_kind=MARKET_MAYHEM`, `source_player_id=None`, `defense_allowed=<если это атака>`, `redirectable=False`;
* беспредел, сыгранный эффектом карты игрока: `source_kind=PLAYER_MAYHEM`, `source_player_id=<player>`, `defense_allowed=<если это атака>`;
* self-damage: `source_kind=SELF`, приз не выдаёт.

Тесты:

```text
test_player_card_damage_has_player_source
test_legend_group_attack_has_neutral_source
test_market_mayhem_has_neutral_source
test_player_played_mayhem_has_player_source
test_source_kind_serialized_in_replay
```

---

## 4. Главный приз Крутагидона

Добавь в `GameState`:

```python
trophy_controller_id: int | None = None
```

или эквивалентное поле.

Правила:

```text
- когда игрок приканчивает врага своим эффектом, он получает Главный приз;
- если игрок убил себя сам, приз не выдаётся;
- если смерть от групповой атаки легенды, приз не выдаётся;
- если смерть от беспредела с барахолки, приз не выдаётся;
- если игрок сыграл карту беспредела эффектом своей карты и убил врага, этот игрок может получить приз;
- пока игрок контролирует приз, в конце своего хода он берёт 6 карт и сбрасывает 1.
```

Реализация:

* `handle_player_death` должен получать `EffectRequest` или source metadata;
* trophy меняет владельца только при корректном kill source;
* событие смены trophy пишется в event log и replay;
* конец хода с trophy должен создать pending choice `discard_one_after_trophy_draw`;
* `RandomAgent` должен уметь выбрать карту для сброса;
* если pending choice пока слишком рискован, разрешается временный auto-discard, но только с явным `TODO` и записью в `docs/progress_stage_2_6_2.md`.

Тесты:

```text
test_trophy_awarded_when_player_kills_enemy_with_card
test_trophy_not_awarded_on_self_kill
test_trophy_not_awarded_on_legend_group_attack_death
test_trophy_not_awarded_on_market_mayhem_death
test_trophy_awarded_on_player_played_mayhem_kill
test_trophy_controller_draws_six_discards_one_at_end_turn
test_trophy_change_logged_and_serialized
```

---

## 5. Исправить group attack lifecycle

В Stage 2.6.1 уже исправлялась цель групповой атаки, но нужно проверить полный lifecycle.

Проблема, которую нужно обязательно проверить:

```text
end_turn раскрывает новую легенду;
resolve_group_attack может создать DEFENSE_WINDOW;
после этого end_turn не должен перетирать фазу обратно в MAIN и терять defense window.
```

Требования:

* групповая атака легенды целит всех колдунов;
* порядок целей начинается со следующего игрока;
* каждый игрок может сыграть защиту;
* если создан `DEFENSE_WINDOW`, ход не должен перейти в обычный `MAIN`, пока атака не разрешена;
* после завершения групповой атаки ход переходит к следующему игроку;
* групповая атака не имеет player-attacker;
* familiar redirect против групповой атаки не должен наносить урон предыдущему игроку, потому что source не является игроком и `redirectable=False`;
* смерть от групповой атаки не выдаёт trophy.

Тесты:

```text
test_end_turn_legend_reveal_preserves_defense_window
test_group_attack_resumes_turn_after_defense_window_resolved
test_group_attack_targets_all_wizards_from_next_player
test_group_attack_defense_available_to_each_target
test_group_attack_familiar_redirect_does_not_hit_previous_player
test_group_attack_death_does_not_award_trophy
```

---

## 6. Исправить mayhem pipeline

Важно: **не меняй начальный setup рынка неверно.**

Правило начального setup:

```text
если беспредел попал в изначальный ассортимент барахолки, он кладётся в стопку уничтоженных карт беспредела и заменяется; эффект не разыгрывается.
```

Правило во время игры:

```text
когда беспредел попадает на барахолку во время пополнения рынка, заполнение временно приостанавливается, беспредел полностью разыгрывается, затем кладётся в mayhem discard/destroyed mayhem pile, после чего рынок продолжает пополняться до 5.
```

Что сделать:

* раздели `fill_initial_market` и `fill_market_during_game`, если сейчас это один метод;
* для initial setup беспределы НЕ разыгрываются;
* для gameplay fill беспределы идут через mayhem pipeline;
* market size после mayhem должен быть 5, если в основной колоде хватает карт;
* если основной колоды не хватает, game-end condition должен срабатывать корректно;
* mayhem attack даёт defense window всем целям по порядку от активного игрока;
* effects against attacker from defense do not trigger for market mayhem because there is no attacker;
* source_kind для market mayhem = `MARKET_MAYHEM`;
* смерть от market mayhem не выдаёт trophy;
* неизвестный mayhem в `strict=True` должен падать понятной ошибкой;
* в `strict=False` неизвестный mayhem логируется и не применяет ложный эффект.

Минимально поддерживаемые паттерны mayhem:

```text
- каждый колдун получает N урона;
- каждый колдун получает вялую палочку;
- каждый колдун сбрасывает N карт;
- каждый колдун может сбросить руку и взять 2 карты, иначе получает вялую палочку;
- примени групповую атаку текущей легенды.
```

Если pending choice для mayhem-choice слишком большой, реализуй только request shell + RandomAgent choice, а сложный mayhem оставь `partial_unsafe`.

Тесты:

```text
test_initial_market_mayhem_is_discarded_without_effect
test_gameplay_market_mayhem_is_resolved
test_gameplay_market_mayhem_pauses_and_refills_market_to_five
test_market_mayhem_attack_opens_defense_window
test_market_mayhem_defense_prevents_effect_for_that_wizard
test_market_mayhem_familiar_redirect_has_no_player_attacker
test_market_mayhem_death_does_not_award_trophy
test_unknown_mayhem_logs_in_non_strict
test_unknown_mayhem_raises_in_strict
test_mayhem_apply_current_legend_group_attack_uses_group_attack_pipeline
```

---

## 7. Защиты и перенаправление

Требования:

* защита доступна против обычных атак, групповых атак и атак беспредела, если source allows defense;
* защита защищает только самого защитившегося игрока;
* защита не отменяет не-атакующие свойства карты атакующего;
* familiar redirect работает только если `redirectable=True` и есть `source_player_id`;
* атакующий не может защититься от перенаправленного эффекта;
* величина эффекта при перенаправлении сохраняется, а не пересчитывается по параметрам атакующего;
* если source не redirectable, familiar defense всё равно может избежать атаки и применить свои draw/heal эффекты, но не наносит redirect-эффект в несуществующего атакующего.

Тесты:

```text
test_defense_prevents_damage
test_defense_draw_text_applies
test_familiar_redirects_player_card_damage
test_attacker_cannot_defend_against_redirect
test_redirect_uses_original_computed_amount
test_familiar_defense_against_non_redirectable_source_does_not_redirect
test_defense_does_not_cancel_non_attack_text
```

---

## 8. Pending choices вместо silent auto-choice

Нельзя автоматически уничтожать/сбрасывать/получать карту там, где игрок должен выбрать, если это влияет на стратегию.

Проверь эффекты:

```text
DestroyCard
DiscardCards
GainCard
ChooseTarget
Trophy discard
Mayhem choices
Weakest/strongest tie choices
```

Требования:

* если выбор нужен, создаётся `pending_choice`;
* `LegalActionGenerator` выдаёт только легальные варианты;
* `RandomAgent` выбирает случайно из legal actions;
* старые auto-choice допустимы только для тестовых helper-функций или явно безопасных случаев;
* replay должен показывать выбор.

Тесты:

```text
test_destroy_from_hand_creates_pending_choice
test_destroy_from_discard_creates_pending_choice
test_discard_choice_creates_pending_choice
test_gain_from_market_choice_creates_pending_choice
test_random_agent_resolves_pending_choice
test_replay_records_pending_choice_resolution
```

---

## 9. Ongoing triggers: только минимальный shell + 2-3 безопасных кейса

Не пытайся реализовать все постоянки.

Добавь структурный event context:

```python
@dataclass
class TriggerEvent:
    name: str
    player_id: int
    card_instance_id: str | None = None
    card_id: str | None = None
    card_type: str | None = None
    amount: int | None = None
    target_player_id: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
```

Минимум:

* `on_start_turn`;
* `on_end_turn`;
* `on_card_played`;
* `on_card_bought`;
* `on_damage_dealt`;
* `on_enemy_killed`.

Реализовать можно только безопасные кейсы:

```text
- "когда ты первый раз за ход разыгрываешь заклинание, бери 1 карту";
- "разыгрываемые тобой атаки наносят удвоенный урон";
- "каждый раз, когда ты убиваешь врага, клади эту карту в сброс" для соответствующей ongoing-карты.
```

Если карта распознана как ongoing, но trigger не реализован:

* `strict=False`: логировать `partial_unsafe` или `not_implemented`;
* `strict=True`: падать понятной ошибкой.

Тесты:

```text
test_ongoing_stays_in_play
test_ongoing_trigger_event_has_context
test_first_spell_per_turn_draws_one_once
test_attack_damage_doubled_by_ongoing
test_ongoing_discards_after_enemy_kill_if_text_says_so
test_unimplemented_ongoing_trigger_raises_in_strict
```

---

## 10. Familiar setup: только если не ломает ядро

Правило:

```text
игрок получает 2 случайных кандидата-фамильяра, выбирает одного, второй уходит из партии;
выбранный фамильяр лежит под планшетом и не работает до покупки;
после покупки уходит в сброс и дальше работает как обычная карта.
```

Если реализация выбора из двух слишком затрагивает setup, сделай только структурную подготовку:

```text
player.familiar_candidates: list[card_id]
player.unbought_familiar_id: card_id | None
player.familiar_purchased: bool
```

Для RandomAgent:

* на setup выбирает случайного кандидата;
* второй удаляется из партии.

Тесты:

```text
test_player_gets_two_familiar_candidates_at_setup
test_random_agent_selects_one_familiar
test_unselected_familiar_removed_from_game
test_unbought_familiar_not_counted_for_vp
test_purchased_familiar_goes_to_discard
test_purchased_familiar_defense_requires_card_in_hand
```

Если не успеешь, оставь это на Stage 2.7 и явно напиши в progress.

---

## 11. Effect coverage и strict mode

Текущий coverage не должен создавать иллюзию полной реализации.

Обнови статусы:

```text
implemented_with_tests
implemented
partial_safe
partial_unsafe
not_implemented
no_effect
data_error
```

Правила:

* `implemented_with_tests` — только если паттерн/карта явно покрыты тестом или listed registry;
* `partial_safe` — часть текста пропущена, но она не меняет состояние игры или явно безопасна;
* `partial_unsafe` — часть текста может менять состояние игры; `strict=True` должен падать;
* `not_implemented` — эффекта нет в engine;
* `no_effect` — реально нет эффекта, например Пшик / Вялая палочка;
* `data_error` — проблема в данных.

Добавь registry, например:

```text
src/game/implemented_patterns.py
```

или другой явный список, чтобы `implemented_with_tests` не ставился только по эвристике.

`effect_coverage` должен показывать:

```text
total_cards
implemented_with_tests
implemented
partial_safe
partial_unsafe
not_implemented
no_effect
data_error
top_missing_mechanics
top_partial_unsafe_cards
top_not_implemented_cards
```

Тесты:

```text
test_implemented_with_tests_requires_registry_entry
test_partial_unsafe_raises_in_strict
test_partial_safe_logs_in_non_strict
test_no_effect_cards_classified_correctly
test_coverage_reports_top_missing_mechanics
```

---

## 12. Replay/debug improvements

Replay должен фиксировать:

```text
source_kind
damage events
death events
trophy changes
defense offered/used/declined
redirect attempts and whether redirectable
mayhem revealed/resolved/discarded
group attack started/resolved
pending choice created/resolved
partial_unsafe/not_implemented effects
end reason
final scores
```

`replay_summary` должен показывать:

```text
seed
players
winner
turn_count
end_reason
final_scores
deaths_by_source_kind
trophy_changes
mayhems_revealed_count
group_attacks_count
defenses_offered_count
defenses_used_count
defenses_declined_count
redirects_count
pending_choices_count
partial_unsafe_count
not_implemented_count
top_partial_unsafe_cards
top_not_implemented_cards
```

Тесты:

```text
test_replay_contains_source_kind
test_replay_contains_trophy_changes
test_replay_contains_defense_decisions
test_replay_contains_mayhem_events
test_replay_summary_counts_deaths_by_source_kind
test_replay_summary_counts_partial_and_unimplemented
```

---

## 13. Документация Stage 2.6.2

Обнови:

```text
README.md
docs/decisions.md
docs/engine_architecture.md
docs/effect_coverage.md
```

Создай:

```text
docs/progress_stage_2_6_2.md
```

В отчёте укажи:

```text
- что было исправлено;
- какие rule-fidelity ошибки закрыты;
- какие тесты добавлены;
- какие команды реально прогнаны;
- падает ли strict и на чём;
- какие механики остались partial_unsafe/not_implemented;
- можно ли переходить к Stage 2.7;
- если нельзя, что ещё блокирует.
```

---

# Definition of Done для Stage 2.6.2

Stage 2.6.2 считается завершённым, если:

```text
pytest проходит;
python -m src.game.validate_manifest проходит;
python -m src.game.effect_coverage проходит;
симуляции 2/3/5 игроков проходят в strict=False;
ЖДК дают -3 VP;
максимум жизней = 25;
смерть возвращает к 20 жизням;
source_kind есть для урона и смертей;
Главный приз реализован;
смерть от group attack и market mayhem не выдаёт приз;
group attack lifecycle не теряет DEFENSE_WINDOW;
market mayhem during gameplay идёт через pipeline с защитами;
initial market mayhem НЕ разыгрывается, а уходит в destroyed mayhem pile и заменяется;
защита/redirect работают корректно для player attack / non-player attack;
pending choices созданы для destroy/discard/gain/trophy discard;
coverage различает partial_safe и partial_unsafe;
strict падает только на понятных partial_unsafe/not_implemented эффектах, не на стартовых картах;
replay_summary показывает source_kind, trophy, defense, mayhem, group_attack;
docs/progress_stage_2_6_2.md создан.
```

Если эти условия не выполнены, **не начинай Stage 2.7**.

---

# Stage 2.7 — Scripted Agents and Evaluation

Начинай только после завершения Stage 2.6.2.

Цель Stage 2.7: не RL, а scripted agents, evaluation и подготовка observation/action model.

## 1. Agent API cleanup

Проверь, что все агенты работают только через:

```python
observation = build_observation(state, player_id)
legal_actions = LegalActionGenerator(state).get_legal_actions(player_id)
action = agent.choose_action(observation, legal_actions)
```

Требования:

* агент не видит скрытые карты чужих колод/рук;
* агент видит свои карты в руке;
* агент видит публичные зоны;
* агент видит рынок, открытую легенду, trophy controller;
* агент видит размеры колод/сбросов/рук врагов;
* agent action всегда legal;
* illegal action приводит к понятной ошибке.

Тесты:

```text
test_observation_hides_enemy_hand
test_observation_includes_own_hand
test_observation_includes_market_and_legend
test_agent_action_must_be_legal
```

## 2. Scripted agents

Добавь агентов:

```text
RandomAgent — уже есть, но привести к новому API;
GreedyBuyAgent — играет карты, покупает самую дорогую доступную карту;
AggressiveAgent — приоритет атак, целей с низким health, добивания ради trophy;
EconomyAgent — приоритет мощи, добора, уничтожения Пшиков/Вялых палочек;
DefenseAwareAgent — использует защиты ценнее, чем RandomAgent;
HeuristicAgent — комбинирует правила выше.
```

Требования:

* агенты не должны читать скрытую информацию;
* агенты должны уметь отвечать на pending choices;
* агенты должны уметь отвечать на defense window;
* агенты должны быть детерминируемыми при seed, если используется random tie-breaker;
* если legal_actions пустой, это ошибка состояния, а не повод делать random noop.

Тесты:

```text
test_greedy_buy_agent_buys_most_expensive_affordable
test_aggressive_agent_prefers_lethal_attack
test_aggressive_agent_targets_low_health_enemy
test_economy_agent_prioritizes_trash_removal
test_defense_aware_agent_uses_defense_against_high_damage
test_heuristic_agent_returns_legal_action_for_pending_choice
test_agents_are_deterministic_with_seed
```

## 3. Evaluation command

Добавь команду:

```bash
python -m src.agents.evaluate --agents random,greedy,aggressive,economy,heuristic --players 3 --games 100 --seed 100 --out data/evaluations/stage_2_7.json
```

Минимальные CLI-опции:

```text
--agents
--players
--games
--seed
--max-turns
--strict
--out
--replay-dir optional
```

Отчёт должен содержать:

```text
agent_name
games_played
wins
winrate
avg_vp
avg_turns
avg_deaths
avg_trophy_turns
avg_cards_bought
avg_legends_defeated
avg_unimplemented_effects
avg_partial_unsafe_effects
crashes
```

Markdown summary:

```text
docs/agent_evaluation_stage_2_7.md
```

Тесты:

```text
test_evaluate_command_writes_json
test_evaluate_summary_contains_all_agents
test_evaluation_counts_wins
test_evaluation_handles_crash_and_records_it
```

## 4. Документация Stage 2.7

Создай:

```text
docs/plan_stage_2_7.md
docs/progress_stage_2_7.md
docs/agent_api.md
docs/agent_evaluation_stage_2_7.md
```

Обнови:

```text
README.md
docs/engine_architecture.md
docs/decisions.md
```

В `docs/progress_stage_2_7.md` укажи:

```text
- какие агенты добавлены;
- какие команды добавлены;
- результаты проверки;
- winrate baseline;
- ограничения scripted-агентов;
- что блокирует RL;
- рекомендации для Stage 2.8.
```

---

# Финальные проверки всей итерации

В конце запусти:

```bash
pytest
python -m src.game.validate_manifest
python -m src.game.effect_coverage
python -m src.game.simulate --players 2 --games 5 --seed 100
python -m src.game.simulate --players 3 --games 10 --seed 100
python -m src.game.simulate --players 5 --games 5 --seed 100
python -m src.game.simulate --players 3 --games 1 --seed 100 --replay-dir data/replays
python -m src.game.replay_summary data/replays/<latest>.json
```

Если Stage 2.7 реализован:

```bash
python -m src.agents.evaluate --agents random,greedy,aggressive,economy,heuristic --players 3 --games 30 --seed 100 --out data/evaluations/stage_2_7_smoke.json
```

Strict:

```bash
python -m src.game.simulate --players 3 --games 1 --seed 100 --strict
```

Если strict падает, это допустимо только на `partial_unsafe` или `not_implemented` эффектах. В отчёте нужно указать:

```text
карта
эффект
source_kind
почему это ожидаемо
какой stage должен это закрыть
```

---

# Итоговый приоритет, если времени мало

Выполняй строго в таком порядке:

```text
1. Smoke baseline.
2. Scoring/health/death reset.
3. SourceKind + trophy.
4. Group attack lifecycle bug.
5. Mayhem pipeline with correct initial setup behavior.
6. Defense/redirect normalization.
7. Pending choices for destroy/discard/gain/trophy.
8. Coverage/strict/replay improvements.
9. Documentation.
10. Only then scripted agents.
```

Главное правило: **лучше честный `partial_unsafe/not_implemented`, чем silent-wrong симуляция**.
::: 
