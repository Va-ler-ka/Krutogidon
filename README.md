# Крутагидон: цифровой движок

Проект переносит настольную deck-building игру в проверяемую цифровую среду. Текущий фокус: этап 1, импорт правил и карт из локальных PDF-сканов.

## Быстрый старт

```powershell
pip install pymupdf pillow pytest
python -m src.importers.run_import
python -m src.importers.xlsx_cards
python -m src.game.simulate --players 3 --games 10
pytest
```

## Текущий статус

- Входные PDF автоматически классифицируются на правила и листы карт.
- Правила извлекаются из текстового слоя PDF.
- Листы карт рендерятся, предобрабатываются и режутся на отдельные изображения.
- `cards.json` создается без догадок: нераспознанные поля остаются пустыми, а карты получают `needs_review`.
- OCR сделан опциональным. Если системный Tesseract не установлен, импорт продолжает работу и формирует очередь ручной проверки.
- Ручная таблица `data/processed/cards_full.xlsx` используется как источник игровых данных для движка.
- Headless-прототип умеет запускать партии между RandomAgent-ботами.

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
