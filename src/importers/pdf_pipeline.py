from __future__ import annotations

import json
import math
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import fitz
from PIL import Image, ImageEnhance, ImageOps


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
PROCESSED_DIR = DATA_DIR / "processed"
PAGES_DIR = PROCESSED_DIR / "pages"
CARD_IMAGES_DIR = PROCESSED_DIR / "card_images"
OCR_DIR = PROCESSED_DIR / "ocr"
REVIEW_DIR = DATA_DIR / "review"


@dataclass(frozen=True)
class PdfInventory:
    rules_files: list[Path]
    card_scan_files: list[Path]


@dataclass(frozen=True)
class PageArtifact:
    source_pdf: Path
    page_number: int
    raw_image: Path
    processed_image: Path
    crop_offset: tuple[int, int]


@dataclass(frozen=True)
class CardCrop:
    source_pdf: Path
    page_number: int
    bbox: tuple[int, int, int, int]
    image_path: Path


def ensure_dirs() -> None:
    for directory in [PAGES_DIR, CARD_IMAGES_DIR, OCR_DIR, REVIEW_DIR]:
        directory.mkdir(parents=True, exist_ok=True)


def slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^\wа-яё]+", "_", value, flags=re.IGNORECASE)
    value = re.sub(r"_+", "_", value).strip("_")
    return value or "item"


def discover_pdfs(root: Path = ROOT) -> PdfInventory:
    pdfs = sorted(root.glob("*.pdf"), key=lambda p: p.name.lower())
    rules: list[Path] = []
    scans: list[Path] = []
    for pdf in pdfs:
        lower_name = pdf.name.lower()
        text_chars = extract_text_char_count(pdf, max_pages=2)
        if "rule" in lower_name or "прав" in lower_name or text_chars > 500:
            rules.append(pdf)
        else:
            scans.append(pdf)
    return PdfInventory(rules_files=rules, card_scan_files=scans)


def extract_text_char_count(pdf_path: Path, *, max_pages: int = 2) -> int:
    try:
        with fitz.open(pdf_path) as doc:
            total = 0
            for index in range(min(max_pages, doc.page_count)):
                total += len(doc.load_page(index).get_text().strip())
            return total
    except Exception:
        return 0


def render_pdf_pages(pdf_path: Path, *, dpi: int = 150, max_dimension: int = 2600) -> list[PageArtifact]:
    artifacts: list[PageArtifact] = []
    with fitz.open(pdf_path) as doc:
        for page_index in range(doc.page_count):
            page = doc.load_page(page_index)
            dpi_scale = dpi / 72
            dimension_scale = max_dimension / max(page.rect.width, page.rect.height)
            scale = min(dpi_scale, dimension_scale)
            matrix = fitz.Matrix(scale, scale)
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            stem = slugify(pdf_path.stem)
            raw_path = PAGES_DIR / f"{stem}_p{page_index + 1:03d}_raw.png"
            processed_path = PAGES_DIR / f"{stem}_p{page_index + 1:03d}_processed.png"
            pix.save(raw_path)
            crop_offset = preprocess_page(raw_path, processed_path)
            artifacts.append(
                PageArtifact(
                    source_pdf=pdf_path,
                    page_number=page_index + 1,
                    raw_image=raw_path,
                    processed_image=processed_path,
                    crop_offset=crop_offset,
                )
            )
    return artifacts


def preprocess_page(raw_path: Path, output_path: Path) -> tuple[int, int]:
    image = Image.open(raw_path).convert("RGB")
    bbox = find_non_white_bbox(image, threshold=248)
    offset = (0, 0)
    if bbox:
        image = image.crop(bbox)
        offset = (bbox[0], bbox[1])
    image = ImageOps.autocontrast(image, cutoff=1)
    image = ImageEnhance.Contrast(image).enhance(1.15)
    image.save(output_path)
    return offset


def find_non_white_bbox(image: Image.Image, *, threshold: int = 248) -> tuple[int, int, int, int] | None:
    gray = image.convert("L")
    inverted = gray.point(lambda px: 255 if px < threshold else 0)
    return inverted.getbbox()


def load_overrides(path: Path | None = None) -> dict[str, Any]:
    override_path = path or (REVIEW_DIR / "segmentation_overrides.json")
    if not override_path.exists():
        return {}
    return json.loads(override_path.read_text(encoding="utf-8"))


def segment_page(page: PageArtifact, *, overrides: dict[str, Any] | None = None) -> list[tuple[int, int, int, int]]:
    override_boxes = get_override_boxes(page, overrides or {})
    if override_boxes is not None:
        return override_boxes

    image = Image.open(page.processed_image).convert("RGB")
    boxes = detect_grid_boxes(image)
    if boxes:
        return boxes

    # Conservative fallback: keep the page as one review item instead of losing data.
    width, height = image.size
    return [(0, 0, width, height)]


def get_override_boxes(page: PageArtifact, overrides: dict[str, Any]) -> list[tuple[int, int, int, int]] | None:
    candidates = [
        page.source_pdf.name,
        page.source_pdf.stem,
        slugify(page.source_pdf.stem),
    ]
    for key in candidates:
        file_override = overrides.get(key)
        if not isinstance(file_override, dict):
            continue
        page_override = file_override.get(str(page.page_number))
        if page_override is None:
            continue
        boxes: list[tuple[int, int, int, int]] = []
        for box in page_override:
            if isinstance(box, list) and len(box) == 4:
                boxes.append(tuple(int(value) for value in box))
        return boxes
    return None


def detect_grid_boxes(image: Image.Image) -> list[tuple[int, int, int, int]]:
    width, height = image.size
    max_work_dimension = 1100
    if max(width, height) > max_work_dimension:
        scale = max_work_dimension / max(width, height)
        work_size = (max(1, int(width * scale)), max(1, int(height * scale)))
        work_image = image.resize(work_size)
        work_boxes = detect_grid_boxes(work_image)
        scaled_boxes: list[tuple[int, int, int, int]] = []
        for x, y, w, h in work_boxes:
            rough = (
                int(x / scale),
                int(y / scale),
                int(math.ceil(w / scale)),
                int(math.ceil(h / scale)),
            )
            if trim_box(image, rough, pad=0):
                scaled_boxes.append(rough)
        return sorted(dedupe_boxes(scaled_boxes), key=lambda box: (box[1], box[0]))

    width, height = image.size
    gray = image.convert("L")
    pixels = gray.load()
    col_counts = []
    for x in range(width):
        count = 0
        for y in range(height):
            if pixels[x, y] < 242:
                count += 1
        col_counts.append(count / height)

    row_counts = []
    for y in range(height):
        count = 0
        for x in range(width):
            if pixels[x, y] < 242:
                count += 1
        row_counts.append(count / width)

    x_runs = projection_runs(col_counts, min_fraction=0.006, min_size=max(80, width // 20), max_gap=width // 80)
    y_runs = projection_runs(row_counts, min_fraction=0.006, min_size=max(120, height // 20), max_gap=height // 100)

    if len(x_runs) * len(y_runs) < 2:
        return detect_regular_card_grid(image)

    boxes: list[tuple[int, int, int, int]] = []
    for y0, y1 in y_runs:
        for x0, x1 in x_runs:
            trimmed = trim_box(image, (x0, y0, x1 - x0, y1 - y0), pad=0)
            if not trimmed:
                continue
            x, y, w, h = trimmed
            area = w * h
            aspect = w / h if h else 0
            if area < (width * height * 0.015):
                continue
            if 0.45 <= aspect <= 0.95:
                boxes.append((x, y, w, h))

    boxes = sorted(dedupe_boxes(boxes), key=lambda box: (box[1], box[0]))
    regular_boxes = detect_regular_card_grid(image)
    if len(regular_boxes) >= max(2, len(boxes)):
        return regular_boxes
    return boxes if len(boxes) >= 2 else regular_boxes


def detect_regular_card_grid(image: Image.Image) -> list[tuple[int, int, int, int]]:
    content = dense_content_bbox(image)
    if not content:
        return []

    left, top, right, bottom = content
    content_width = right - left
    content_height = bottom - top
    if content_width <= 0 or content_height <= 0:
        return []

    target_aspect = 0.715
    candidates: list[tuple[float, int, int]] = []
    for cols in (3, 2, 1):
        cell_width = content_width / cols
        estimated_rows = max(1, min(5, round(content_height / (cell_width / target_aspect))))
        for rows in {estimated_rows, estimated_rows + 1, estimated_rows - 1}:
            if rows < 1 or rows > 5:
                continue
            cell_height = content_height / rows
            aspect = cell_width / cell_height
            score = abs(aspect - target_aspect) + (0 if cols == 3 else 0.08 * (3 - cols))
            candidates.append((score, cols, rows))

    _score, cols, rows = min(candidates, key=lambda item: item[0])
    cell_width = content_width / cols
    cell_height = content_height / rows
    boxes: list[tuple[int, int, int, int]] = []

    for row in range(rows):
        for col in range(cols):
            x0 = int(round(left + col * cell_width))
            y0 = int(round(top + row * cell_height))
            x1 = int(round(left + (col + 1) * cell_width))
            y1 = int(round(top + (row + 1) * cell_height))
            inset_x = max(1, int(round(cell_width * 0.008)))
            inset_y = max(1, int(round(cell_height * 0.02)))
            cell_box = (
                min(x1 - 1, x0 + inset_x),
                min(y1 - 1, y0 + inset_y),
                max(1, (x1 - x0) - 2 * inset_x),
                max(1, (y1 - y0) - 2 * inset_y),
            )
            trimmed = trim_box(image, cell_box, pad=0)
            if not trimmed:
                continue
            x, y, w, h = trimmed
            if w * h < cell_width * cell_height * 0.55:
                continue
            aspect = w / h if h else 0
            if 0.45 <= aspect <= 0.95:
                boxes.append(cell_box)

    return sorted(dedupe_boxes(boxes), key=lambda box: (box[1], box[0]))


def dense_content_bbox(image: Image.Image) -> tuple[int, int, int, int] | None:
    width, height = image.size
    gray = image.convert("L")
    pixels = gray.load()

    col_counts = []
    for x in range(width):
        count = 0
        for y in range(height):
            if pixels[x, y] < 245:
                count += 1
        col_counts.append(count / height)

    row_counts = []
    for y in range(height):
        count = 0
        for x in range(width):
            if pixels[x, y] < 245:
                count += 1
        row_counts.append(count / width)

    x_indices = [index for index, value in enumerate(col_counts) if value > 0.03]
    y_indices = [index for index, value in enumerate(row_counts) if value > 0.03]
    if not x_indices or not y_indices:
        return find_non_white_bbox(image, threshold=248)

    pad = 8
    return (
        max(0, min(x_indices) - pad),
        max(0, min(y_indices) - pad),
        min(width, max(x_indices) + pad),
        min(height, max(y_indices) + pad),
    )


def projection_runs(
    values: list[float],
    *,
    min_fraction: float,
    min_size: int,
    max_gap: int,
) -> list[tuple[int, int]]:
    occupied = [value >= min_fraction for value in values]
    fill_small_gaps(occupied, max_gap=max_gap)

    runs: list[tuple[int, int]] = []
    start: int | None = None
    for index, is_occupied in enumerate(occupied):
        if is_occupied and start is None:
            start = index
        elif not is_occupied and start is not None:
            if index - start >= min_size:
                runs.append((start, index))
            start = None
    if start is not None and len(occupied) - start >= min_size:
        runs.append((start, len(occupied)))
    return runs


def fill_small_gaps(occupied: list[bool], *, max_gap: int) -> None:
    index = 0
    while index < len(occupied):
        if occupied[index]:
            index += 1
            continue
        start = index
        while index < len(occupied) and not occupied[index]:
            index += 1
        end = index
        left = start > 0 and occupied[start - 1]
        right = end < len(occupied) and occupied[end]
        if left and right and end - start <= max_gap:
            for fill_index in range(start, end):
                occupied[fill_index] = True


def trim_box(image: Image.Image, box: tuple[int, int, int, int], *, pad: int = 4) -> tuple[int, int, int, int] | None:
    x, y, w, h = box
    crop = image.crop((x, y, x + w, y + h))
    bbox = find_non_white_bbox(crop, threshold=248)
    if not bbox:
        return None
    x0, y0, x1, y1 = bbox
    return (
        max(0, x + x0 - pad),
        max(0, y + y0 - pad),
        min(image.size[0], x + x1 + pad) - max(0, x + x0 - pad),
        min(image.size[1], y + y1 + pad) - max(0, y + y0 - pad),
    )


def dedupe_boxes(boxes: list[tuple[int, int, int, int]]) -> list[tuple[int, int, int, int]]:
    kept: list[tuple[int, int, int, int]] = []
    for box in boxes:
        if all(intersection_over_union(box, other) < 0.7 for other in kept):
            kept.append(box)
    return kept


def intersection_over_union(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> float:
    ax0, ay0, aw, ah = a
    bx0, by0, bw, bh = b
    ax1, ay1 = ax0 + aw, ay0 + ah
    bx1, by1 = bx0 + bw, by0 + bh
    ix0, iy0 = max(ax0, bx0), max(ay0, by0)
    ix1, iy1 = min(ax1, bx1), min(ay1, by1)
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    intersection = (ix1 - ix0) * (iy1 - iy0)
    union = aw * ah + bw * bh - intersection
    return intersection / union if union else 0.0


def save_card_crops(pages: list[PageArtifact], *, overrides: dict[str, Any] | None = None) -> list[CardCrop]:
    crops: list[CardCrop] = []
    for page in pages:
        image = Image.open(page.processed_image).convert("RGB")
        boxes = segment_page(page, overrides=overrides)
        stem = slugify(page.source_pdf.stem)
        for index, (x, y, w, h) in enumerate(boxes, start=1):
            card_image = image.crop((x, y, x + w, y + h))
            image_name = f"{stem}_p{page.page_number:03d}_c{index:02d}.png"
            image_path = CARD_IMAGES_DIR / image_name
            card_image.save(image_path)
            crops.append(
                CardCrop(
                    source_pdf=page.source_pdf,
                    page_number=page.page_number,
                    bbox=(x, y, w, h),
                    image_path=image_path,
                )
            )
    return crops


def extract_rules(rules_files: list[Path]) -> tuple[str, dict[str, Any]]:
    parts: list[str] = []
    for pdf in rules_files:
        with fitz.open(pdf) as doc:
            for page_index in range(doc.page_count):
                text = doc.load_page(page_index).get_text().strip()
                if text:
                    parts.append(f"\n\n=== {pdf.name} / page {page_index + 1} ===\n{text}")
    rules_text = "\n".join(parts).strip()
    (PROCESSED_DIR / "rules_text.txt").write_text(rules_text, encoding="utf-8")

    summary = {
        "source_files": [pdf.name for pdf in rules_files],
        "text_extracted": bool(rules_text),
        "sections": {
            "components": find_snippets(rules_text, ["Состав", "Компоненты", "карты"]),
            "setup": find_snippets(rules_text, ["Подготовка", "начинает", "стартов"]),
            "turn_order": find_snippets(rules_text, ["Ход", "В свой ход", "конец хода"]),
            "attacks": find_snippets(rules_text, ["Атака", "Защита", "группов"]),
            "scoring": find_snippets(rules_text, ["Побед", "очки", "конец игры"]),
        },
        "needs_review": True,
        "notes": "Summary is mechanically extracted and must be checked against the rulebook before engine implementation.",
    }
    (PROCESSED_DIR / "rules_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_rules_model(summary)
    return rules_text, summary


def find_snippets(text: str, keywords: list[str], *, limit: int = 4) -> list[str]:
    if not text:
        return []
    normalized = re.sub(r"\s+", " ", text)
    snippets: list[str] = []
    for keyword in keywords:
        pattern = re.compile(re.escape(keyword), re.IGNORECASE)
        for match in pattern.finditer(normalized):
            start = max(0, match.start() - 180)
            end = min(len(normalized), match.end() + 360)
            snippet = normalized[start:end].strip()
            if snippet not in snippets:
                snippets.append(snippet)
            if len(snippets) >= limit:
                return snippets
    return snippets


def write_rules_model(summary: dict[str, Any]) -> None:
    path = ROOT / "docs" / "rules_model.md"
    path.write_text(
        """# Модель правил

Документ фиксирует формальную модель для будущего движка. Он создан на этапе импорта из локального rulebook PDF и требует ручной сверки перед реализацией спорных эффектов.

## Состав игры

- Личные зоны игроков: колода, рука, сброс, сыгранные карты, уничтоженные карты.
- Общие зоны: основная колода, барахолка, стопка легенд, шальная магия, вялые палочки, жетоны свойств, жетоны дохлых колдунов.
- Отдельные объекты: планшеты колдунов и фамильяры.

## Типы карт

- Массовые карты / стартовые карты.
- Заклинания.
- Сокровища.
- Твари.
- Места.
- Беспределы.
- Легенды.
- Фамильяры.
- Волшебники / планшеты колдунов.
- Свойства и дохлые колдуны представлены отдельными жетонами/картами и требуют сверки по сканам.

## Подготовка партии

- Игроки начинают с 20 жизнями.
- Стартовая колода игрока: 6 знаков, 1 палочка, 3 пшика.
- Игрок берет стартовую руку из 5 карт.
- Барахолка содержит 5 открытых карт.
- Легенды, шальная магия, вялые палочки, фамильяры и жетоны размещаются отдельными стопками/зонами.

## Ход игрока

- Обработать эффекты начала хода и постоянки.
- Разыгрывать карты с руки в выбранном порядке.
- Накопить мощь и выполнить эффекты карт.
- Покупать карты с барахолки и из доступных стопок.
- Атаковать врагов и/или побеждать легенду при наличии условий.
- Завершить ход, сбросить непостоянные сыгранные карты и добрать новую руку.

## Конец хода

- Купленные и полученные карты обычно отправляются в сброс, если текст карты не говорит иначе.
- Непостоянные сыгранные карты уходят в сброс.
- Постоянки остаются под контролем игрока.
- Игрок добирает 5 карт, перемешивая сброс при пустой колоде.
- При победе над легендой новая легенда раскрывается в конце хода и запускает групповую атаку.

## Атака и защита

- Атака может иметь одиночную цель, всех врагов или специальный способ выбора цели.
- Цель может применить защиту с руки, если эффект позволяет.
- Защита не отменяет остальные свойства сыгранной защитной карты.
- Групповые атаки применяются в порядке, указанном правилами; точный порядок требует ручной сверки.

## Фамильяры

- Фамильяры стартуют под планшетом и не действуют, пока не куплены.
- Купленный фамильяр становится отдельным управляемым объектом игрока.
- Эффекты фамильяров, особенно защиты/перенаправления, требуют ручной разметки.

## Постоянки

- При розыгрыше остаются в игре.
- Действуют, пока находятся под контролем игрока.
- Не сбрасываются в конце хода, если эффект не говорит иначе.

## Сброс, уничтожение и получение карт

- Сброс игрока перемешивается в новую колоду при попытке добора из пустой колоды.
- Уничтоженные карты покидают обычный цикл колода-рука-сброс.
- Полученные карты по умолчанию попадают в сброс.

## Конец игры и очки

- Игра заканчивается при исчерпании легенд, невозможности пополнить барахолку до 5 карт или окончании стопки дохлых колдунов.
- Очки считаются по победным очкам на картах и штрафам.
- Особые VP-эффекты карт будут реализованы как расширяемые функции.
- Tie-breaker: больше легенд, затем меньше жетонов дохлых колдунов.

## Needs Review

- Точный текст и условия всех эффектов карт.
- Полный список типов и подтипов карт.
- Точные правила групповой атаки и порядка реакции защит.
- Точные штрафы дохлых колдунов и вялых палочек.
- Точные условия покупки/активации фамильяров.
""",
        encoding="utf-8",
    )


def reset_generated_outputs() -> None:
    for directory in [PAGES_DIR, CARD_IMAGES_DIR, OCR_DIR]:
        if directory.exists():
            shutil.rmtree(directory)
        directory.mkdir(parents=True, exist_ok=True)


def relative_to_root(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT)).replace("\\", "/")
