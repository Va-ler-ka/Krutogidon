from __future__ import annotations

import argparse
import json
from pathlib import Path

from .ocr_cards import ocr_image
from .pdf_pipeline import (
    PROCESSED_DIR,
    REVIEW_DIR,
    ROOT,
    discover_pdfs,
    ensure_dirs,
    extract_rules,
    load_overrides,
    relative_to_root,
    render_pdf_pages,
    reset_generated_outputs,
    save_card_crops,
)
from .schema import make_card_record, validate_card_record


def build_cards_json(card_crops) -> list[dict]:
    records = []
    for index, crop in enumerate(card_crops, start=1):
        engine, raw_text, confidence = ocr_image(crop.image_path)
        card_id = f"krutagidon_{crop.source_pdf.stem}_{crop.page_number:03d}_{index:04d}"
        record = make_card_record(
            card_id=card_id,
            source_file=crop.source_pdf.name,
            page=crop.page_number,
            bbox=[int(value) for value in crop.bbox],
            image_path=relative_to_root(crop.image_path),
            raw_text=raw_text,
            ocr_engine=engine,
            confidence=confidence,
        )
        records.append(record)
    return records


def write_json_outputs(cards: list[dict]) -> None:
    validation_errors = {
        card.get("id", f"card_{index}"): validate_card_record(card)
        for index, card in enumerate(cards)
        if validate_card_record(card)
    }
    if validation_errors:
        raise ValueError(f"Invalid card records: {validation_errors}")

    cards_path = PROCESSED_DIR / "cards.json"
    cards_path.write_text(json.dumps(cards, ensure_ascii=False, indent=2), encoding="utf-8")

    needs_review = [card for card in cards if card["ocr"]["needs_review"]]
    review_path = REVIEW_DIR / "cards_needs_review.json"
    review_path.write_text(
        json.dumps(needs_review, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def write_import_report(*, inventory, pages_count: int, cards: list[dict]) -> None:
    confident = [card for card in cards if not card["ocr"]["needs_review"]]
    needs_review = [card for card in cards if card["ocr"]["needs_review"]]
    report = {
        "rules_files": [path.name for path in inventory.rules_files],
        "card_scan_files": [path.name for path in inventory.card_scan_files],
        "rendered_pages": pages_count,
        "cards_found": len(cards),
        "cards_confident": len(confident),
        "cards_needs_review": len(needs_review),
        "ocr_engines": sorted({card["ocr"]["engine"] for card in cards}),
    }
    (PROCESSED_DIR / "import_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    docs_report = ROOT / "docs" / "progress_stage_1.md"
    docs_report.write_text(
        f"""# Отчет по этапу 1

## Сделано

- Найдены файлы правил: {", ".join(report["rules_files"]) or "нет"}.
- Найдены PDF со сканами карт: {len(report["card_scan_files"])}.
- Отрендерено страниц карт: {pages_count}.
- Создано изображений карт: {len(cards)}.
- Создан `data/processed/cards.json`.
- Создан `data/review/cards_needs_review.json`.
- Созданы `data/processed/rules_summary.json` и `docs/rules_model.md`.

## Результаты импорта

- Уверенно распознано карт: {len(confident)}.
- Требуют проверки: {len(needs_review)}.
- OCR engines: {", ".join(report["ocr_engines"]) or "none"}.

## Known Issues

- Системный Tesseract не обязателен; если он отсутствует, все карты попадают в ручную проверку.
- Автоматическая сегментация основана на сетке и может ошибаться на нестандартных листах.
- Для исправления сегментации можно создать `data/review/segmentation_overrides.json`.
- Поля карт пока не заполняются по догадке.

## Следующие шаги

- Проверить изображения в `data/processed/card_images/`.
- При необходимости добавить manual overrides для листов с неверной нарезкой.
- Подключить OCR или выполнить ручную разметку критичных полей карт.
""",
        encoding="utf-8",
    )


def write_import_docs() -> None:
    (ROOT / "docs" / "import_pipeline.md").write_text(
        """# Пайплайн импорта

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
""",
        encoding="utf-8",
    )

    decisions = ROOT / "docs" / "decisions.md"
    existing = decisions.read_text(encoding="utf-8") if decisions.exists() else ""
    entry = """# Решения

## 2026-06-21. Минимальный стек импорта

- Используем Python 3.11+ как основной язык проекта.
- Для рендера PDF выбран PyMuPDF: он работает напрямую с локальными PDF и не требует системного Poppler.
- Для предобработки изображений выбран Pillow: достаточно для первого воспроизводимого пайплайна.
- OCR сделан опциональным. Без Tesseract карты не распознаются по догадке, а попадают в `needs_review`.
- Сегментация сначала реализована как projection/grid алгоритм без OpenCV, чтобы снизить входной порог запуска.
"""
    if "2026-06-21. Минимальный стек импорта" not in existing:
        decisions.write_text(entry if not existing else existing.rstrip() + "\n\n" + entry, encoding="utf-8")


def run_import(*, dpi: int = 150, max_dimension: int = 2600, clean: bool = True) -> dict:
    ensure_dirs()
    if clean:
        reset_generated_outputs()

    inventory = discover_pdfs(ROOT)
    rules_text, _rules_summary = extract_rules(inventory.rules_files)

    overrides = load_overrides()
    page_artifacts = []
    for pdf in inventory.card_scan_files:
        page_artifacts.extend(render_pdf_pages(pdf, dpi=dpi, max_dimension=max_dimension))

    card_crops = save_card_crops(page_artifacts, overrides=overrides)
    cards = build_cards_json(card_crops)
    write_json_outputs(cards)
    write_import_report(inventory=inventory, pages_count=len(page_artifacts), cards=cards)
    write_import_docs()

    return {
        "rules_files": len(inventory.rules_files),
        "card_scan_files": len(inventory.card_scan_files),
        "rules_text_chars": len(rules_text),
        "rendered_pages": len(page_artifacts),
        "cards_found": len(cards),
        "cards_needs_review": sum(1 for card in cards if card["ocr"]["needs_review"]),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import Krutagidon rules and card scans.")
    parser.add_argument("--dpi", type=int, default=150)
    parser.add_argument("--max-dimension", type=int, default=2600)
    parser.add_argument("--no-clean", action="store_true", help="Keep existing generated page/card images.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_import(dpi=args.dpi, max_dimension=args.max_dimension, clean=not args.no_clean)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
