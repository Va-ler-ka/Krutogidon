# Крутагидон: цифровой движок

Проект переносит настольную deck-building игру в проверяемую цифровую среду. Текущий фокус: строгий headless-движок правил, пригодный для будущих агентов.

## Быстрый старт

```powershell
pip install pymupdf pillow pytest
python -m src.importers.run_import
python -m src.importers.xlsx_cards
python -m src.game.simulate --players 3 --games 10
python -m src.game.validate_manifest
python -m src.game.effect_coverage
python -m src.game.simulate --players 3 --games 1 --seed 100 --replay-dir data/replays
python -m src.game.replay_summary data/replays/<replay>.json
pytest
```

## Текущий статус

- Входные PDF автоматически классифицируются на правила и листы карт.
- Правила извлекаются из текстового слоя PDF.
- Листы карт рендерятся, предобрабатываются и режутся на отдельные изображения.
- `cards.json` создается без догадок: нераспознанные поля остаются пустыми, а карты получают `needs_review`.
- OCR сделан опциональным. Если системный Tesseract не установлен, импорт продолжает работу и формирует очередь ручной проверки.
- Ручная таблица `data/processed/cards_full.xlsx` используется как источник игровых данных для движка.
- Headless-движок умеет запускать партии между RandomAgent-ботами.
- В состоянии есть явные фазы, pending choice и defense window.
- Legal actions генерируются централизованно через `LegalActionGenerator`.
- Простые эффекты работают через primitive effects: мощь, добор, лечение, урон.
- Есть базовая поддержка targeting, защит, постоянок, беспределов, смерти и жетонов дохлых колдунов.
- Отчет покрытия эффектов сохраняется в `data/processed/effect_coverage.json`.
- Стопки собираются из `data/processed/deck_manifest.json`.
- Игровые зоны используют физические копии карт `CardInstance`.
- Вум всегда первая открытая легенда; число легенд зависит от числа игроков.
- Фамильяр начинает под планшетом, покупается в сброс и дальше работает как обычная карта.
- Текст карт разделяется на секции: main, attack, defense, ongoing, group attack, scoring.
- Симуляция умеет писать replay/debug JSON.

Последний запуск этапа 1:

- rulebook: 1 PDF;
- card scans: 11 PDF;
- rendered pages: 20;
- card images: 169;
- confident OCR cards: 0;
- needs review: 169.

## Основные команды

```powershell
python -m src.importers.run_import
python -m src.importers.xlsx_cards
python -m src.game.simulate --players 3 --games 10
python -m src.game.validate_manifest
python -m src.game.effect_coverage
python -m src.game.simulate --players 3 --games 1 --seed 100 --replay-dir data/replays
python -m src.game.simulate --players 3 --games 1 --seed 100 --strict
pytest
```

Будущие этапы добавят:

```powershell
python -m src.agents.evaluate --agent random --games 100
python -m src.agents.train --config configs/train_default.yaml
uvicorn src.api.main:app --reload
```

## Структура

```text
data/
  processed/
    card_images/
    cards.json
    rules_summary.json
  review/
    cards_needs_review.json
docs/
src/
  importers/
  game/
  agents/
tests/
```

## Статус эффекта карт

```powershell
python -m src.game.effect_coverage
```

Команда печатает сводку по реализованности эффектов и сохраняет подробный JSON-отчет в `data/processed/effect_coverage.json`.
Markdown-версия сохраняется в `docs/effect_coverage.md`.

`--strict` ожидаемо может падать на нереализованных эффектах. Это режим проверки полноты реализации, а не обычный режим симуляции.

## Диагностика replay

```powershell
python -m src.game.simulate --players 3 --games 1 --seed 100 --replay-dir data/replays
python -m src.game.replay_summary data/replays/<replay>.json
```

`replay_summary` печатает компактную JSON-сводку по seed, числу игроков, действиям, событиям, покупкам, атакам, защитам, смертям, победителям и coverage snapshot.
После Stage 2.6.2 в сводку также входят `source_kind`, смерти по источникам, смены Главного приза, group attack, defense/redirect и partial/not_implemented счетчики.
