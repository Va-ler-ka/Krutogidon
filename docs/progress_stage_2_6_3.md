# Progress Stage 2.6.3

Дата: 2026-06-28.

## Что сделано

- Расширен `PendingChoice`: добавлены `choice_id`, `options`, source metadata, min/max bounds и metadata для продолжения отложенных цепочек.
- `LegalActionGenerator` теперь строит `CHOOSE_TARGET` actions из generic pending-choice options с `option_id`.
- `GameEngine` умеет разрешать pending choices для trophy discard, destroy, discard, gain и market mayhem target choice.
- Конец хода контроллера Главного приза больше не auto-discards карту: создается `trophy_discard` pending choice, а после выбора продолжается обычный end-turn flow.
- `DestroyCard`, `DiscardCards` и `GainCard` создают pending choice, когда есть несколько легальных вариантов.
- `беспредел_10` закрыт через mayhem handler `play_each_market_attack`.
- Market mayhem attacks используют `source_kind=market_mayhem`, не имеют `source_player_id`, разрешают defense window и не выдают Главный приз за смерть.
- Для `беспредел_10` сложные динамические attack-секции карт с барахолки не применяются молча: в non-strict логируется `partial_unsafe`, в strict выбрасывается понятный `NotImplementedError` с id рыночной карты.
- Market refill приостанавливается, если беспредел открыл pending choice или defense window, и продолжается после разрешения.
- Replay summary дополнен pending-choice counters, auto-choice counters и mayhem handler diagnostics.
- Coverage report дополнен `mayhem_blockers` и `pending_choice_blockers`.
- Убрана запись `cards_full.json` из `load_card_database()`, чтобы параллельные проверки не спорили за generated файл.

## Беспредел 10

`беспредел_10` больше не является `not_implemented`.

Реализовано:

- поиск attack-карт на текущей барахолке;
- применение только attack-секции, без main text;
- простые damage attacks;
- weak wand attacks;
- discard-one attacks через pending choice, если у игрока больше одной карты;
- target choice для атак по выбранному врагу/колдуну;
- defense window через общий damage pipeline;
- redirect ignored для нейтрального market mayhem source.

Ограничение остается честным: динамический урон вроде "за каждую..." или "столько урона, какова стоимость..." остается `partial_unsafe`/strict error.

## Pending choices

Реализованы production pending choices:

- `trophy_discard`;
- `destroy_card`;
- `discard_card`;
- `gain_card`;
- `choose_market_attack_target`.

RandomAgent уже выбирает один из legal actions для этих окон, потому что они представлены обычным `CHOOSE_TARGET`.

## Coverage

Последний `python -m src.game.effect_coverage`:

- total_cards: 113;
- implemented_with_tests: 13;
- partial_safe: 0;
- partial_unsafe: 71;
- not_implemented: 27;
- no_effect: 2;
- percent_implemented_or_partial: 76.11%.

## Strict

`python -m src.game.simulate --players 3 --games 1 --seed 100 --strict` больше не падает на `беспредел_10`.

Текущий strict blocker:

```text
сокровище_большой_костец:
Постоянка: пока не начался подсчёт очков, считается, что у тебя под контролем дополнительный жетон долгого колдуна...
```

Это ongoing/scoring mechanic и хороший кандидат для Stage 2.6.4.

## Проверки

Прогнано:

```powershell
python -m pytest -q
python -m src.game.validate_manifest
python -m src.game.effect_coverage
python -m src.game.simulate --players 2 --games 5 --seed 100
python -m src.game.simulate --players 3 --games 10 --seed 100
python -m src.game.simulate --players 5 --games 5 --seed 100
python -m src.game.simulate --players 3 --games 1 --seed 100 --replay-dir data/replays
python -m src.game.replay_summary data/replays/game_100_20260628_004209.json
python -m src.game.simulate --players 3 --games 1 --seed 100 --strict
```

Результаты:

- `pytest`: 123 passed;
- `validate_manifest`: ok, errors `[]`;
- `effect_coverage`: ok;
- simulations 2/3/5 players strict=False: ok;
- replay summary: ok, показывает `pending_choices_created_count=49`, `pending_choices_resolved_count=49`, `auto_choices_count=0`, `mayhem_handlers_used={"play_each_market_attack": 1}`;
- strict: ожидаемо падает на `сокровище_большой_костец`, не на `беспредел_10`.

## Осталось для Stage 2.6.4

- ongoing/scoring effects, в первую очередь `сокровище_большой_костец`;
- более полные эффекты фамильяров;
- более глубокие dynamic attack patterns;
- выборы с несколькими последовательными решениями и optional "may" ветками;
- дальнейшее снижение `partial_unsafe` и `not_implemented`.

Stage 2.7 scripted agents не начинался.
