from __future__ import annotations

import json
from pathlib import Path

from src.importers.schema import make_card_record, validate_card_record


def test_card_schema_accepts_minimal_review_record() -> None:
    card = make_card_record(
        card_id="test_card",
        source_file="cards.pdf",
        page=1,
        bbox=[1, 2, 300, 420],
        image_path="data/processed/card_images/test.png",
    )

    assert validate_card_record(card) == []
    assert card["ocr"]["needs_review"] is True
    assert card["implementation"]["status"] == "not_implemented"


def test_card_schema_rejects_bad_bbox() -> None:
    card = make_card_record(
        card_id="test_card",
        source_file="cards.pdf",
        page=1,
        bbox=[1, 2, 300, 420],
        image_path="data/processed/card_images/test.png",
    )
    card["source"]["bbox"] = [1, 2, 3]

    errors = validate_card_record(card)

    assert "source.bbox must be a list of four integers" in errors


def test_generated_cards_json_is_valid_when_present() -> None:
    cards_path = Path("data/processed/cards.json")
    if not cards_path.exists():
        return

    cards = json.loads(cards_path.read_text(encoding="utf-8"))

    assert isinstance(cards, list)
    assert cards
    assert all(validate_card_record(card) == [] for card in cards)


def test_generated_review_file_contains_only_review_cards_when_present() -> None:
    review_path = Path("data/review/cards_needs_review.json")
    if not review_path.exists():
        return

    cards = json.loads(review_path.read_text(encoding="utf-8"))

    assert isinstance(cards, list)
    assert all(card["ocr"]["needs_review"] is True for card in cards)
