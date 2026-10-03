"""Small deterministic lexical utilities for the offline baseline."""

from __future__ import annotations

import json
import re

from models.schemas import Evidence

STOPWORDS = frozenset(
    "a an and are as at be been by can could do does for from had has have how i in is it "
    "me my of on or please should that the their this to was what when where which why will "
    "with would you your tell explain about after without".split()
)


def terms(text: str) -> set[str]:
    tokens = re.findall(r"\d+(?:\.\d+)+|[a-z0-9][a-z0-9_:/-]*", text.casefold())
    result = {
        token[:-1] if len(token) > 4 and token.endswith("s") else token
        for token in tokens
        if token not in STOPWORDS
    }
    for run in re.findall(r"[\u4e00-\u9fff]+", text):
        result.update(run[i : i + 2] for i in range(max(1, len(run) - 1)))
    return result


def token_count(text: str) -> int:
    """Portable estimate, not the tokenizer of a specific language model."""
    return len(re.findall(r"[A-Za-z0-9_:/-]+|[\u4e00-\u9fff]|[^\s]", text))


def serialize_evidence(evidence: list[Evidence]) -> str:
    data = [
        {
            "source_id": e.source_id,
            "source_file": e.source_file,
            "page_number": e.page_number,
            "excerpt": e.excerpt,
            "title": e.title,
            "applicability": e.applicability,
        }
        for e in evidence
    ]
    # Escape markup delimiters so document text cannot close the external-data boundary.
    payload = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e")
    return "<retrieved_context>\n" + payload + "\n</retrieved_context>"
