# Пайплайн импорта

Команда:

```powershell
python -m src.importers.run_import
```

## Шаги

1. Поиск PDF в корне проекта.
2. Классификация:
   - PDF с текстовым слоем или названием `rulebook` считается правилами.
   - Остальные PDF считаются листами карт.
3. Рендер страниц карт через PyMuPDF в `data/processed/pages/`.
4. Предобработка:
   - обрезка белых полей;
   - autocontrast;
   - небольшое повышение контраста.
5. Сегментация:
   - анализ горизонтальных и вертикальных проекций непустых пикселей;
   - сохранение отдельных карт в `data/processed/card_images/`;
   - координаты bbox сохраняются в JSON.
6. OCR:
   - если доступны Tesseract и pytesseract, запускается OCR `rus+eng`;
   - если OCR недоступен или неуверен, карта получает `needs_review`.
7. Выходы:
   - `data/processed/cards.json`;
   - `data/review/cards_needs_review.json`;
   - `data/processed/import_report.json`;
   - `data/processed/rules_summary.json`;
   - `docs/rules_model.md`.

## Manual Overrides

Если автоматическая сегментация ошиблась, создайте файл:

```json
{
  "волшебники.pdf": {
    "1": [[10, 20, 300, 420], [330, 20, 300, 420]]
  }
}
```

Координаты задаются в пикселях относительно `*_processed.png` страницы.
