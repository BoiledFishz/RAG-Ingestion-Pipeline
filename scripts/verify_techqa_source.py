"""Inventory original records, including unusable rows, without modifying the source."""

from __future__ import annotations

import bz2
import json
import logging

import ijson

from rag.techqa.data import DATA_ROOT, ROOT, normalize


def main() -> None:
    count, usable = 0, 0
    invalid, seen, duplicates = [], set(), []
    with bz2.open(DATA_ROOT / "technote_corpus/full_technote_collection.txt.bz2", "rb") as stream:
        for row in ijson.items(stream, "item", multiple_values=True):
            count += 1
            doc = normalize(row)
            if not doc:
                invalid.append(
                    {
                        "id": row.get("id"),
                        "title": row.get("title"),
                        "reason": "missing id or empty text",
                    }
                )
                continue
            usable += 1
            if doc["id"] in seen:
                duplicates.append(doc["id"])
            seen.add(doc["id"])
    result = {
        "source_records": count,
        "usable_records": usable,
        "unique_usable_documents": len(seen),
        "invalid_records": invalid,
        "duplicate_ids": duplicates,
    }
    target = ROOT / "evals/techqa_source_inventory.json"
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    logging.info("Official source inventory: %s", result)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
