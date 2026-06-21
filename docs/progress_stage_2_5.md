# Отчет по этапу 2.5

## Сделано

- Добавлены явные фазы игры: `MAIN`, `CHOOSE_TARGET`, `DEFENSE_WINDOW`, `RESOLVING_EFFECT`, `END_OF_TURN`, `LEGEND_REVEAL`, `GAME_OVER`.
- Добавлены `pending_choice`, `effect_queue` и `dead_wizard_stack` в состояние.
- Создан `LegalActionGenerator`; `RandomAgent` выбирает только из переданных legal actions.
- Создан слой targeting selectors.
- Эффекты разложены на primitive effects:
  - `GainPower`;
  - `DrawCards`;
  - `Heal`;
  - `DealDamage`;
  - `DiscardCards`;
  - `DestroyCard` shell;
  - `GainCard` shell;
  - `GiveWeakWand`;
  - `RevealHand`;
  - `ConditionalEffect` shell;
  - `CompositeEffect`.
- Добавлен defense window:
  - отказ от защиты;
  - защита с руки;
  - базовый добор/лечение из текста защиты;
  - перенаправление урона фамильяром.
- Постоянки остаются в `ongoing`; добавлен trigger shell.
- Беспределы не занимают слот барахолки, логируются и уходят в отдельный discard.
- Добавлена базовая смерть: жетон дохлого колдуна, восстановление здоровья по временной константе, конец игры при пустом стеке.
- Добавлена команда отчета:

```powershell
python -m src.game.effect_coverage
```

## Добавленные тесты

- `test_legal_actions.py`
- `test_phases.py`
- `test_targeting.py`
- `test_defense.py`
- `test_ongoing.py`
- `test_bespredel.py`
- `test_death.py`
- `test_effect_coverage.py`

## Проверка

```powershell
pytest
python -m src.game.simulate --players 3 --games 10 --seed 100
python -m src.game.effect_coverage
```

Последний результат: тесты проходят, 10/10 симуляций завершаются без падений.

## Все еще не реализовано полностью

- Индивидуальные сложные тексты большинства карт.
- Полные эффекты беспределов.
- Полные групповые атаки легенд, кроме простого извлекаемого урона.
- Полные свойства и постоянные trigger-эффекты.
- Выбор карт для сброса/уничтожения/получения.
- Точное правило восстановления после смерти требует сверки.

## Готово для этапа 3

- Стабильная фазовая модель.
- Сериализуемые legal actions.
- Pending target/defense choices.
- RandomAgent, который не конструирует действия вручную.
- Effect coverage как инструмент контроля прогресса.

## Блокеры полноценного RL

- Нужна более полная реализация карты за картой.
- Нужны observation/action encoders поверх legal action mask.
- Нужны replay/seed diagnostics.
- Нужны scripted-агенты для baseline-оценки.
