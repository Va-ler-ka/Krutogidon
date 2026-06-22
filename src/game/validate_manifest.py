from __future__ import annotations

import json
import sys

from .data import load_card_database
from .deck_manifest import validate_main_deck_manifest


def main() -> None:
    database = load_card_database()
    report = validate_main_deck_manifest(database.manifest, database)
    summary = {
        "main_deck_physical_count": report["main_deck_physical_count"],
        "mayhem_unique_count": len(report["mayhem"]),
        "singleton_non_mayhem_count": len(report["singleton_non_mayhem"]),
        "double_unique_count": len(report["double"]),
        "double_physical_count": report["double_physical_count"],
        "errors": report["errors"],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if report["errors"]:
        print("\nManifest groups:", file=sys.stderr)
        print(json.dumps({key: report[key] for key in ["mayhem", "singleton_non_mayhem", "double", "missing", "extra", "wrong_quantity"]}, ensure_ascii=False, indent=2), file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
