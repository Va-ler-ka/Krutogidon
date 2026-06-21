from __future__ import annotations

from typing import Any


REQUIRED_CARD_KEYS = {
    "id",
    "name",
    "type",
    "set",
    "cost",
    "victory_points",
    "power",
    "text",
    "keywords",
    "attack",
    "defense",
    "ongoing",
    "group_attack",
    "source",
    "ocr",
    "implementation",
}


def make_card_record(
    *,
    card_id: str,
    source_file: str,
    page: int,
    bbox: list[int],
    image_path: str,
    raw_text: str = "",
    ocr_engine: str = "none",
    confidence: float | None = None,
) -> dict[str, Any]:
    needs_review = confidence is None or confidence < 0.85 or not raw_text.strip()
    return {
        "id": card_id,
        "name": "",
        "type": "",
        "set": "krutagidon",
        "cost": None,
        "victory_points": None,
        "power": 0,
        "text": "",
        "keywords": [],
        "attack": False,
        "defense": False,
        "ongoing": False,
        "group_attack": False,
        "source": {
            "file": source_file,
            "page": page,
            "bbox": bbox,
            "image_path": image_path,
        },
        "ocr": {
            "engine": ocr_engine,
            "confidence": confidence,
            "needs_review": needs_review,
            "raw_text": raw_text,
        },
        "implementation": {
            "effect_id": None,
            "status": "not_implemented",
            "notes": "Imported from scan; card fields require OCR/manual review.",
        },
    }


def validate_card_record(card: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = REQUIRED_CARD_KEYS - set(card)
    if missing:
        errors.append(f"missing keys: {sorted(missing)}")

    source = card.get("source")
    if not isinstance(source, dict):
        errors.append("source must be an object")
    else:
        bbox = source.get("bbox")
        if not (
            isinstance(bbox, list)
            and len(bbox) == 4
            and all(isinstance(value, int) for value in bbox)
        ):
            errors.append("source.bbox must be a list of four integers")
        if not source.get("file"):
            errors.append("source.file is required")
        if not source.get("image_path"):
            errors.append("source.image_path is required")

    ocr = card.get("ocr")
    if not isinstance(ocr, dict):
        errors.append("ocr must be an object")
    elif "needs_review" not in ocr:
        errors.append("ocr.needs_review is required")

    implementation = card.get("implementation")
    if not isinstance(implementation, dict):
        errors.append("implementation must be an object")
    elif not implementation.get("status"):
        errors.append("implementation.status is required")

    if not isinstance(card.get("keywords"), list):
        errors.append("keywords must be a list")
    if not isinstance(card.get("power"), int):
        errors.append("power must be an integer")

    return errors
