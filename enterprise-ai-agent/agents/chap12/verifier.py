"""Answerability Verifier (round 5, 2026-10-19).

After the RAG Worker publishes an answer, the Supervisor asks the model one separate question:
do the quoted passages of the cited documents actually answer the user's question? If the
model says no, the Supervisor withholds the explanation (RAG result -> no_data, category
invalid_evidence) instead of publishing an answer built on related-but-wrong documents.

Motivation (tune split, real model, round 4 base): 32 of 38 unanswerable questions were
answered anyway; reranker-score refusal signals never reached balanced accuracy 0.6.
The model sees only the question, the answer and the cited quotes; it cannot add citations or
change the answer, only veto it. Any model error or invalid output keeps the answer
(fail-open), and is counted, so the Verifier can never turn a model outage into refusals.
Enabled by CHAP12_VERIFIER=on/off, else `adopted.verifier` in tune/real_config.json, else off.

Round 6 (graded): the binary Verifier saw only the short quotes and vetoed 12 answers that
cited the gold document. The graded mode shows the model the evidence passages the answer was
generated from (Citation.excerpt) and asks for a 1-5 score; the Supervisor withholds the
answer only below a minimum score chosen on the tune split. CHAP12_VERIFIER=graded with no
minimum records scores without vetoing anything (used to choose the minimum).
"""

from __future__ import annotations

import json
import os
from typing import Any

from agents.chap12.contracts import RagPayload
from models.errors import DependencyUnavailable

PROMPT = (
    "KIND: ANSWER_VERIFY\n"
    "You check a technical-support answer before it is shown to the user.\n"
    "Decide whether the QUOTES taken from the cited IBM documents actually answer the "
    "QUESTION. Answer false when the quotes only discuss a related topic, a different "
    "product, version, component or error, or do not contain the specific cause, fix or "
    "information the question asks for. Answer true only when a reader could resolve the "
    "question from the quotes.\n"
    "Return JSON {{\"answers\": true}} or {{\"answers\": false}} only.\n\n"
    "QUESTION:\n{query}\n\nANSWER:\n{answer}\n\nQUOTES:\n{quotes}")
MAX_QUOTES_CHARS = 3000
GRADED_PROMPT = (
    "KIND: ANSWER_GRADE\n"
    "You check a technical-support answer before it is shown to the user.\n"
    "Read the QUESTION and the EVIDENCE passages from the cited IBM documents, then rate how "
    "well the EVIDENCE answers the QUESTION:\n"
    "5 = the evidence states the specific cause, fix or information asked for;\n"
    "4 = it mostly answers it; a reader could act on it;\n"
    "3 = partly relevant; key details are missing or uncertain;\n"
    "2 = same topic, but a different product, version, component or error;\n"
    "1 = unrelated.\n"
    "Return JSON {{\"score\": <1-5>}} only.\n\n"
    "QUESTION:\n{query}\n\nANSWER:\n{answer}\n\nEVIDENCE:\n{evidence}")
MAX_PASSAGE_CHARS = 2500
MAX_EVIDENCE_CHARS = 6000
Mode = tuple[str, int | None]


def verifier_enabled(default: bool | None = None) -> bool:
    configured = os.getenv("CHAP12_VERIFIER", "")
    if configured in {"on", "off"}:
        return configured == "on"
    return bool(default)


def verifier_mode(default: bool | None = None, default_min: int | None = None) -> Mode:
    """(mode, min_score). mode: off | on (binary, round 5) | graded (round 6).
    Env CHAP12_VERIFIER / CHAP12_VERIFIER_MIN_SCORE win; else tune/real_config.json."""
    configured = os.getenv("CHAP12_VERIFIER", "")
    raw_min = os.getenv("CHAP12_VERIFIER_MIN_SCORE", "")
    minimum = int(raw_min) if raw_min else default_min
    if configured in {"off", "on", "graded"}:
        return configured, minimum if configured == "graded" else None
    if default_min is not None:
        return "graded", minimum
    return ("on" if default else "off"), None


def evidence_text(payload: RagPayload) -> str:
    seen: dict[str, str] = {}
    for c in payload.citations:
        text = (c.excerpt or c.quote).strip()
        key = f"{c.doc_id}:{text[:80]}"
        if key not in seen:
            seen[key] = f"[{c.doc_id}] {c.title}\n{text[:MAX_PASSAGE_CHARS]}"
    return "\n\n".join(seen.values())[:MAX_EVIDENCE_CHARS]


class AnswerVerifier:
    def __init__(self, model: Any) -> None:
        self.model = model
        self.errors = 0

    async def answers(self, query: str, payload: RagPayload) -> bool | None:
        """True/False from the model; None if it could not decide (caller keeps the answer)."""
        quotes = "\n".join(f"[{c.doc_id}] {c.title}: {c.quote}" for c in payload.citations)
        schema = {"type": "object", "required": ["answers"],
                  "properties": {"answers": {"type": "boolean"}}}
        prompt = PROMPT.format(query=query[:2000], answer=payload.answer[:1500],
                               quotes=quotes[:MAX_QUOTES_CHARS])
        try:
            verdict = json.loads(await self.model.generate(prompt, schema)).get("answers")
        except (DependencyUnavailable, ValueError, TypeError, AttributeError):
            self.errors += 1
            return None
        return verdict if isinstance(verdict, bool) else None

    async def grade(self, query: str, payload: RagPayload) -> int | None:
        """1-5 from the model; None if it could not decide (caller keeps the answer)."""
        schema = {"type": "object", "required": ["score"],
                  "properties": {"score": {"type": "integer", "minimum": 1, "maximum": 5}}}
        prompt = GRADED_PROMPT.format(query=query[:2000], answer=payload.answer[:1500],
                                      evidence=evidence_text(payload))
        try:
            score = json.loads(await self.model.generate(prompt, schema)).get("score")
        except (DependencyUnavailable, ValueError, TypeError, AttributeError):
            self.errors += 1
            return None
        if isinstance(score, bool) or not isinstance(score, int) or not 1 <= score <= 5:
            return None
        value: int = score
        return value

