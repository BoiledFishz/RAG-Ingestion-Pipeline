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


def verifier_enabled(default: bool | None = None) -> bool:
    configured = os.getenv("CHAP12_VERIFIER", "")
    if configured in {"on", "off"}:
        return configured == "on"
    return bool(default)


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
