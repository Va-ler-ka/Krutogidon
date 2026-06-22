from __future__ import annotations

import re
from dataclasses import dataclass


MARKERS = [
    ("group_attack_text", "Групповая атака:"),
    ("attack_text", "Атака:"),
    ("defense_text", "Защита:"),
    ("ongoing_text", "Постоянка:"),
]


@dataclass(frozen=True)
class CardTextSections:
    main_text: str
    attack_text: str | None
    defense_text: str | None
    ongoing_text: str | None
    group_attack_text: str | None
    scoring_text: str | None
    raw_text: str


def parse_card_text(text: str) -> CardTextSections:
    raw = text or ""
    marker_matches = []
    for section, marker in MARKERS:
        for match in re.finditer(re.escape(marker), raw, flags=re.IGNORECASE):
            marker_matches.append((match.start(), match.end(), section))
    marker_matches.sort(key=lambda item: (item[0], -(item[1] - item[0])))
    filtered = []
    occupied_until = -1
    for item in marker_matches:
        if item[0] < occupied_until:
            continue
        filtered.append(item)
        occupied_until = item[1]
    marker_matches = filtered

    values: dict[str, str | None] = {
        "attack_text": None,
        "defense_text": None,
        "ongoing_text": None,
        "group_attack_text": None,
    }
    main_end = marker_matches[0][0] if marker_matches else len(raw)
    main_text = raw[:main_end].strip()
    for index, (_start, content_start, section) in enumerate(marker_matches):
        content_end = marker_matches[index + 1][0] if index + 1 < len(marker_matches) else len(raw)
        values[section] = raw[content_start:content_end].strip()

    scoring_text = extract_scoring_text(raw)
    return CardTextSections(
        main_text=main_text,
        attack_text=values["attack_text"],
        defense_text=values["defense_text"],
        ongoing_text=values["ongoing_text"],
        group_attack_text=values["group_attack_text"],
        scoring_text=scoring_text,
        raw_text=raw,
    )


def extract_scoring_text(text: str) -> str | None:
    lower = text.lower()
    needles = ["в конце игры", "при подсчёте", "при подсчете", "победн"]
    if not any(needle in lower for needle in needles):
        return None
    sentences = re.split(r"(?<=[.!?])\s+", text)
    selected = [
        sentence.strip()
        for sentence in sentences
        if any(needle in sentence.lower() for needle in needles)
    ]
    return " ".join(selected) if selected else text
