from __future__ import annotations

from pathlib import Path

from src.importers.xlsx_cards import load_cards_database, write_cards_full_json

from .models import CardDatabase, CardDefinition


DEFAULT_XLSX = Path(__file__).resolve().parents[2] / "data" / "processed" / "cards_full.xlsx"


def load_card_database(path: Path = DEFAULT_XLSX) -> CardDatabase:
    extracted = load_cards_database(path)
    write_cards_full_json(extracted)

    cards: dict[str, CardDefinition] = {}
    legends: list[str] = []
    familiars: list[str] = []
    main_deck_cards: list[str] = []
    starter_cards: dict[str, str] = {}
    wild_magic_id: str | None = None
    weak_wand_id: str | None = None
    dead_wizard_tokens = [token.id for token in extracted.dead_wizard_tokens]

    for item in extracted.cards:
        definition = CardDefinition(
            id=item.id,
            name=item.name,
            card_class=item.card_class,
            text=item.text,
            cost=item.cost,
            victory_points=item.victory_points,
            power=item.power,
            keywords=item.keywords,
            attack=item.attack,
            defense=item.defense,
            ongoing=item.ongoing,
            group_attack=item.group_attack,
            source_sheet=item.source_sheet,
            source_file=item.source_file,
            effect_id=infer_effect_id(item.text),
            implementation_status=item.implementation_status,
        )
        cards[definition.id] = definition

        if definition.card_class == "Легенда":
            legends.append(definition.id)
        elif definition.card_class == "Фамильяр":
            familiars.append(definition.id)
        elif definition.name in {"Палочка", "Знак", "Пшик"}:
            starter_cards[definition.name] = definition.id
        elif definition.name == "Шальная магия":
            wild_magic_id = definition.id
        elif definition.name == "Вялая палочка":
            weak_wand_id = definition.id
        elif definition.card_class not in {"Служебная карта", "Шальная магия"}:
            main_deck_cards.append(definition.id)

    mayhem_cards: list[CardDefinition] = []
    for token in extracted.mayhems:
        definition = CardDefinition(
            id=token.id,
            name=f"Беспредел {token.number}",
            card_class="Беспредел",
            text=token.text,
            cost=None,
            victory_points=0,
            keywords=("атака",) if "атака" in token.text.lower() else (),
            attack="атака" in token.text.lower(),
            source_sheet=token.source_sheet,
            source_file=token.source_file,
            implementation_status="not_implemented",
        )
        cards[definition.id] = definition
        mayhem_cards.append(definition)
        main_deck_cards.append(definition.id)

    return CardDatabase(
        cards=cards,
        mayhem_cards=mayhem_cards,
        legends=legends,
        familiars=familiars,
        main_deck_cards=main_deck_cards,
        starter_cards=starter_cards,
        wild_magic_id=wild_magic_id,
        weak_wand_id=weak_wand_id,
        dead_wizard_tokens=dead_wizard_tokens,
    )


def infer_effect_id(text: str) -> str | None:
    effect_parts: list[str] = []
    if "+1 мощ" in text.lower():
        effect_parts.append("gain_power")
    if "возьми" in text.lower() and "карт" in text.lower():
        effect_parts.append("draw_cards")
    if "нанеси" in text.lower() and "урон" in text.lower():
        effect_parts.append("deal_damage")
    return "+".join(effect_parts) if effect_parts else None
