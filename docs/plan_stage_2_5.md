# План этапа 2.5

## Уже реализовано

- Данные карт загружаются из `data/processed/cards_full.xlsx`.
- Создается нормализованный `data/processed/cards_full.json`.
- Есть headless-движок с setup, рынком, ходом, покупками, легендами и scoring.
- `RandomAgent` запускает партии через `python -m src.game.simulate --players 3 --games 10 --seed 100`.
- Простые эффекты частично применяются: мощь, добор, простой урон.
- Все сложные эффекты пока логируются как частично реализованные или не реализованные.

## Ограничения

- Нет явной фазы игры в состоянии.
- `GameEngine.legal_actions()` смешивает генерацию действий с логикой движка.
- Атаки применяются напрямую, без defense window.
- Targeting представлен одним `target_player`.
- Постоянки только остаются в зоне `ongoing`, но не имеют trigger-модели.
- Беспределы и групповые атаки только placeholder.
- Дохлые колдуны учитываются в scoring, но не выдаются при смерти.

## Модули, которые будут изменены

- `src/game/enums.py` - фазы и расширенный набор действий.
- `src/game/models.py` - pending choice/effect, расширенный `Action`, фазовое состояние.
- `src/game/engine.py` - фазовый step, defense window, смерть, легенды, проверка легальности.
- `src/game/effects.py` - primitive effects и resolver.
- `src/game/setup.py` - начальная фаза и стек дохлых колдунов.
- `src/agents/random_agent.py` - выбор только из действий LegalActionGenerator.
- `src/game/simulate.py` - совместимость с новым legal action flow.

## Новые модули

- `src/game/legal_actions.py` - единый генератор легальных действий.
- `src/game/targeting.py` - selectors и выбор целей.
- `src/game/triggers.py` - основа trigger-событий для постоянок.
- `src/game/effect_coverage.py` - отчет покрытия эффектов.

## Новые тесты

- `tests/test_legal_actions.py`
- `tests/test_phases.py`
- `tests/test_targeting.py`
- `tests/test_defense.py`
- `tests/test_ongoing.py`
- `tests/test_bespredel.py`
- `tests/test_effect_coverage.py`

## Риски

- Полный текст всех карт слишком разнообразен для полного покрытия в одном проходе.
- В `cards_full.xlsx` нет тиража карт, поэтому состав основной колоды остается модельным.
- Точное правило восстановления после смерти требует ручной сверки; будет введена временная константа с `TODO_RULE_CLARIFICATION`.
- Строгий режим должен падать на нереализованных групповых атаках/эффектах, но обычная симуляция должна продолжать работать.
