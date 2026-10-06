"""Reference-only fact drafts and blind, independent ordinal scoring."""

from __future__ import annotations

import hashlib
import re
from typing import Any

from evaluation_protocol.storage import STATE, canonical, read, write_new


def fact_drafts(records: list[dict[str, Any]], partition: str) -> dict[str, Any]:
    """Drafts require human verification; never invent facts to meet a numeric quota."""
    items = []
    for wrapped in records:
        row = wrapped["record"]
        if row["ANSWERABLE"] != "Y":
            continue
        answer = row["ANSWER"]
        units = [
            s.strip() for s in re.split(r"\n+|(?<=[.!?])\s+(?=[A-Z0-9])|;\s+", answer) if s.strip()
        ]
        # All candidates are literal official-answer excerpts, with unchanged punctuation.
        unique = list(dict.fromkeys(units))
        chosen = (
            unique
            if len(unique) <= 5
            else [
                unique[i]
                for i in sorted(
                    set(
                        [
                            0,
                            len(unique) - 1,
                            len(unique) // 4,
                            len(unique) // 2,
                            3 * len(unique) // 4,
                        ]
                    )
                )
            ]
        )
        facts = [
            {
                "fact_id": f"F{i}",
                "text": text,
                "reference_quote": text,
                "category": "needs_human_classification",
            }
            for i, text in enumerate(chosen, 1)
        ]
        items.append(
            {
                "question_id": row["QUESTION_ID"],
                "question": [row["QUESTION_TITLE"], row["QUESTION_TEXT"]],
                "official_answer": answer,
                "required_facts": facts,
                "definition_status": "unreviewed_draft",
                "exception": "empty official answer"
                if not answer
                else (
                    "fewer than two distinct facts: human decomposition needed"
                    if len(facts) < 2
                    else None
                ),
                "human_approved": False,
            }
        )
    value = {
        "partition": partition,
        "method": "reference-only literal clause sampling",
        "status": "draft, NOT validated gold",
        "annotator": None,
        "is_human": True,
        "instructions": "Review definitions WITHOUT looking at model responses. Preserve the "
        "official answer. Approve 2-5 distinct required facts, or flag impossible "
        "empty-answer cases; do not add outside knowledge.",
        "items": items,
    }
    write_new(STATE / f"facts_{partition}.draft.json", value)
    # Editable copy is deliberately not represented as frozen human gold.
    (STATE / f"human_facts_{partition}.template.json").write_bytes(canonical(value))
    return value


def fact_signature(facts: list[dict[str, Any]]) -> str:
    return hashlib.sha256(canonical(facts)).hexdigest()


def human_rating_template(
    rows: list[dict[str, Any]], definitions: dict[str, Any], partition: str, output: Any
) -> None:
    facts = {r["question_id"]: r for r in definitions["items"]}
    seen = set()
    items = []
    for row in rows:
        if row["question_id"] not in facts:
            continue
        body = row["native"].get("run") or {}
        answer = body.get("response", {}).get("answer", "")
        answer_sha = hashlib.sha256(answer.encode()).hexdigest()
        pair = row["question_id"], answer_sha
        if pair in seen:
            continue
        seen.add(pair)
        definition = facts[row["question_id"]]
        items.append(
            {
                "question_id": row["question_id"],
                "answer_sha256": answer_sha,
                "facts_sha256": fact_signature(definition["required_facts"]),
                "answer_body": answer,
                "facts": [
                    {**fact, "score": None, "answer_quote": "", "reason": ""}
                    for fact in definition["required_facts"]
                ],
            }
        )
    (output / "human_ratings.template.json").write_bytes(
        canonical(
            {
                "partition": partition,
                "annotator": None,
                "is_human": True,
                "independent": True,
                "definition_gold_status": definitions["status"],
                "instructions": "Score ONLY the answer body, not sources/quotes stored outside it. "
                "0=absent/wrong; 1=partial/underspecified; 2=complete and correct. "
                "Do not inspect the LLM judge ratings before submitting.",
                "items": items,
            }
        )
    )


def validate_human_ratings(payload: dict[str, Any], template: dict[str, Any]) -> None:
    if (
        not payload.get("is_human")
        or not payload.get("independent")
        or not payload.get("annotator")
    ):
        raise ValueError("Named independent human annotator required")
    expected = {(r["question_id"], r["answer_sha256"]): r for r in template["items"]}
    received = {(r["question_id"], r["answer_sha256"]): r for r in payload["items"]}
    if len(received) != len(payload["items"]) or set(expected) != set(received):
        raise ValueError("Human ratings must cover exactly the frozen answer items")
    for key, row in received.items():
        reference = expected[key]
        if (
            row["facts_sha256"] != reference["facts_sha256"]
            or row["answer_body"] != reference["answer_body"]
        ):
            raise ValueError("Changed answer or fact definitions")
        if len(row["facts"]) != len(reference["facts"]):
            raise ValueError("Changed fact set")
        for fact, original in zip(row["facts"], reference["facts"], strict=True):
            if {k: fact[k] for k in original if k not in {"score", "answer_quote", "reason"}} != {
                k: original[k] for k in original if k not in {"score", "answer_quote", "reason"}
            }:
                raise ValueError("Changed required fact")
            if type(fact.get("score")) is not int or fact["score"] not in {0, 1, 2}:
                raise ValueError("Every human fact rating must be integer 0/1/2")
            if fact["score"] and (
                not fact["answer_quote"] or fact["answer_quote"] not in row["answer_body"]
            ):
                raise ValueError("Positive ratings require an exact answer-body evidence quote")


def approved_definitions(partition: str) -> dict[str, Any] | None:
    path = STATE / f"facts_{partition}.human_frozen.json"
    if not path.exists():
        return None
    from evaluation_protocol.storage import verify

    verify(path)
    return read(path)
