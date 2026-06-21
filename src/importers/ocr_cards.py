from __future__ import annotations

import shutil
from pathlib import Path


def ocr_image(image_path: Path) -> tuple[str, str, float | None]:
    """Return (engine, raw_text, confidence).

    OCR is intentionally optional. If Tesseract/pytesseract are not available,
    the caller receives an empty result and must mark the card for review.
    """

    if shutil.which("tesseract") is None:
        return "none", "", None

    try:
        import pytesseract
    except ImportError:
        return "none", "", None

    try:
        data = pytesseract.image_to_data(
            str(image_path),
            lang="rus+eng",
            output_type=pytesseract.Output.DICT,
        )
    except Exception:
        return "tesseract", "", None

    words: list[str] = []
    confidences: list[float] = []
    for text, confidence in zip(data.get("text", []), data.get("conf", []), strict=False):
        text = str(text).strip()
        if not text:
            continue
        words.append(text)
        try:
            numeric = float(confidence)
        except (TypeError, ValueError):
            continue
        if numeric >= 0:
            confidences.append(numeric / 100)

    average_confidence = sum(confidences) / len(confidences) if confidences else None
    return "tesseract", " ".join(words), average_confidence
