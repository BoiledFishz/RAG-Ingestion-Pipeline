"""Answer-body evaluation helpers; source objects never count as generated answers."""

from __future__ import annotations

import re
from collections import Counter


def body_token_f1(answer: str, reference: str) -> float:
    body = re.sub(r"\[(?:S?\d+|evidence)\]", "", answer).casefold()
    expected = Counter(re.findall(r"\w+", reference.casefold()))
    actual = Counter(re.findall(r"\w+", body))
    total = sum(expected.values()) + sum(actual.values())
    return 2 * sum((expected & actual).values()) / total if total else 0.0
