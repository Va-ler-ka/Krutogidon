from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_XLSX = ROOT / "data" / "processed" / "cards_full.xlsx"
DEFAULT_JSON = ROOT / "data" / "processed" / "cards_full.json"

NS = {
    "a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}


@dataclass(frozen=True)
class ExtractedCard:
    id: str
    name: str
    card_class: str
    text: str
    cost: int | None
    victory_points: int
    source_sheet: str
    source_file: str
    subtitle: str = ""
    power: int = 0
    keywords: tuple[str, ...] = ()
    attack: bool = False
    defense: bool = False
    ongoing: bool = False
    group_attack: bool = False
    implementation_status: str = "not_implemented"


@dataclass(frozen=True)
class ExtractedToken:
    id: str
    token_type: str
    text: str
    source_sheet: str
    number: int | None = None
    form: str = ""
    source_file: str = ""


@dataclass(frozen=True)
class ExtractedDatabase:
    cards: tuple[ExtractedCard, ...]
    mayhems: tuple[ExtractedToken, ...]
    dead_wizard_tokens: tuple[ExtractedToken, ...]
    properties: tuple[ExtractedToken, ...]


def load_cards_database(path: Path = DEFAULT_XLSX) -> ExtractedDatabase:
    sheets = read_xlsx(path)
    cards = read_cards(sheets)
    mayhems = read_tokens(sheets, "Беспределы", token_type="Беспредел")
    dead_wizard_tokens = read_tokens(sheets, "Дохлые_колдуны", token_type="Дохлый колдун")
    properties = read_tokens(sheets, "Свойства", token_type="Свойство")
    return ExtractedDatabase(
        cards=tuple(cards),
        mayhems=tuple(mayhems),
        dead_wizard_tokens=tuple(dead_wizard_tokens),
        properties=tuple(properties),
    )


def read_cards(sheets: dict[str, list[dict[str, str]]]) -> list[ExtractedCard]:
    cards: list[ExtractedCard] = []
    seen: set[str] = set()

    for row in sheets.get("Все_карты", []):
        card_class = get_first(row, "класс_карты", "тип")
        name = get_first(row, "название") or card_class
        text = get_first(row, "описание")
        cost = parse_int(get_first(row, "стоимость"))
        victory_points = parse_int(get_first(row, "победные_очки")) or 0
        source_file = get_first(row, "источник")
        subtitle = get_first(row, "подзаголовок")
        if not card_class and not name and not text:
            continue

        card_id = unique_id(slugify(f"{card_class}_{name or text[:24]}"), seen)
        power = parse_power(text)
        keywords = detect_keywords(text)
        cards.append(
            ExtractedCard(
                id=card_id,
                name=name,
                card_class=card_class,
                text=text,
                cost=cost,
                victory_points=victory_points,
                source_sheet="Все_карты",
                source_file=source_file,
                subtitle=subtitle,
                power=power,
                keywords=keywords,
                attack="атака" in keywords,
                defense="защита" in keywords,
                ongoing="постоянка" in keywords,
                group_attack="групповая атака" in keywords,
                implementation_status="partial" if power else "not_implemented",
            )
        )
    return cards


def read_tokens(
    sheets: dict[str, list[dict[str, str]]],
    sheet_name: str,
    *,
    token_type: str,
) -> list[ExtractedToken]:
    tokens: list[ExtractedToken] = []
    seen: set[str] = set()
    for row in sheets.get(sheet_name, []):
        number = parse_int(get_first(row, "№"))
        text = get_first(row, "текст")
        if not text:
            continue
        form = get_first(row, "форма")
        token_subtype = get_first(row, "тип") or token_type
        source_file = get_first(row, "источник")
        token_id = unique_id(slugify(f"{token_type}_{number or text[:24]}"), seen)
        tokens.append(
            ExtractedToken(
                id=token_id,
                token_type=token_subtype,
                text=text,
                source_sheet=sheet_name,
                number=number,
                form=form,
                source_file=source_file,
            )
        )
    return tokens


def write_cards_full_json(
    database: ExtractedDatabase | None = None,
    *,
    output_path: Path = DEFAULT_JSON,
) -> Path:
    database = database or load_cards_database()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "cards": [asdict(card) for card in database.cards],
        "mayhems": [asdict(token) for token in database.mayhems],
        "dead_wizard_tokens": [asdict(token) for token in database.dead_wizard_tokens],
        "properties": [asdict(token) for token in database.properties],
    }
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


def read_xlsx(path: Path) -> dict[str, list[dict[str, str]]]:
    with ZipFile(path) as archive:
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        relmap = {rel.attrib["Id"]: rel.attrib["Target"] for rel in relationships}
        shared_strings = read_shared_strings(archive)

        result: dict[str, list[dict[str, str]]] = {}
        for sheet in workbook.findall("a:sheets/a:sheet", NS):
            name = sheet.attrib["name"]
            rel_id = sheet.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
            path_in_archive = "xl/" + relmap[rel_id].lstrip("/")
            rows = read_sheet_rows(archive, path_in_archive, shared_strings)
            if not rows:
                result[name] = []
                continue
            header = [normalize_header(value) for value in rows[0]]
            mapped_rows: list[dict[str, str]] = []
            for row in rows[1:]:
                mapped = {
                    header[index]: value.strip()
                    for index, value in enumerate(row)
                    if index < len(header) and header[index]
                }
                if any(mapped.values()):
                    mapped_rows.append(mapped)
            result[name] = mapped_rows
    return result


def read_shared_strings(archive: ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    strings: list[str] = []
    for item in root.findall("a:si", NS):
        strings.append("".join(text.text or "" for text in item.findall(".//a:t", NS)))
    return strings


def read_sheet_rows(archive: ZipFile, path: str, shared_strings: list[str]) -> list[list[str]]:
    sheet = ET.fromstring(archive.read(path))
    rows: list[list[str]] = []
    for row in sheet.findall("a:sheetData/a:row", NS):
        values: list[str] = []
        for cell in row.findall("a:c", NS):
            index = column_index(cell.attrib.get("r", "A1"))
            while len(values) <= index:
                values.append("")
            value_node = cell.find("a:v", NS)
            value = "" if value_node is None else value_node.text or ""
            if cell.attrib.get("t") == "s" and value:
                value = shared_strings[int(value)]
            values[index] = value
        if any(value.strip() for value in values):
            rows.append(values)
    return rows


def column_index(cell_ref: str) -> int:
    letters = "".join(char for char in cell_ref if char.isalpha())
    index = 0
    for char in letters:
        index = index * 26 + (ord(char.upper()) - 64)
    return index - 1


def normalize_header(value: str) -> str:
    return value.strip().lower().replace(" ", "_")


def get_first(row: dict[str, str], *keys: str) -> str:
    for key in keys:
        value = row.get(normalize_header(key), "")
        if value:
            return value
    return ""


def parse_int(value: str) -> int | None:
    value = value.strip()
    if not value:
        return None
    match = re.search(r"-?\d+", value)
    return int(match.group(0)) if match else None


def parse_power(text: str) -> int:
    total = 0
    for match in re.finditer(r"\+(\d+)\s*мощ", text.lower()):
        total += int(match.group(1))
    return total


def detect_keywords(text: str) -> tuple[str, ...]:
    lower = text.lower()
    keywords: list[str] = []
    checks = [
        ("групповая атака", "групповая атака"),
        ("атака", "атака"),
        ("защита", "защита"),
        ("постоянка", "постоянка"),
        ("начал", "начало хода"),
        ("конец хода", "конец хода"),
    ]
    for needle, keyword in checks:
        if needle in lower and keyword not in keywords:
            keywords.append(keyword)
    return tuple(keywords)


def slugify(value: str) -> str:
    value = value.lower().replace("ё", "е")
    value = re.sub(r"[^a-zа-я0-9]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value or "item"


def unique_id(base: str, seen: set[str]) -> str:
    candidate = base
    suffix = 2
    while candidate in seen:
        candidate = f"{base}_{suffix}"
        suffix += 1
    seen.add(candidate)
    return candidate


def main() -> None:
    database = load_cards_database()
    path = write_cards_full_json(database)
    print(
        json.dumps(
            {
                "cards": len(database.cards),
                "mayhems": len(database.mayhems),
                "dead_wizard_tokens": len(database.dead_wizard_tokens),
                "properties": len(database.properties),
                "output": str(path),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
