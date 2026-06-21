from __future__ import annotations

from src.importers.xlsx_cards import load_cards_database


def test_cards_full_xlsx_loads_manual_data() -> None:
    database = load_cards_database()

    assert len(database.cards) == 87
    assert len(database.mayhems) == 26
    assert len(database.dead_wizard_tokens) == 20
    assert len(database.properties) == 8
    assert any(card.name == "Палочка" for card in database.cards)
