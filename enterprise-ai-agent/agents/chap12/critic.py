"""Program Critic and the single bounded Replan (item 10).

The Critic is deterministic: it reads the Worker results and never calls a model. It checks
  C1  a published RAG answer has citations, each with a quote and inside the retrieved set;
  C2  the data part is about the product of the documents the answer actually cites.
C2 is the only finding that triggers a Replan, and only when the data product was not given
by the user (source inferred or model_pick) or could not be resolved at all
(clarification_required). The Replan re-runs the DB Worker once with the product of the cited
documents (source "rag_citation"). At most MAX_REPLANS per request; the DB Worker still applies
authorization, budget and deadline, so a Replan can never widen access or exceed the budget.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass, field

from agents.chap12.contracts import DbPayload, RagPayload, WorkerResult

MAX_REPLANS = 1
REPLACEABLE = {"inferred", "model_pick"}


def critic_enabled(default: bool | None = None) -> bool:
    """CHAP12_CRITIC=on/off wins; otherwise `default` (the online profile passes the value
    chosen on the tune split with the real model, evaluation/chap12/tune/real_config.json);
    otherwise off (offline tune rule not met: results/chap12/tune_critic_on vs _off)."""
    configured = os.getenv("CHAP12_CRITIC", "")
    if configured in {"on", "off"}:
        return configured == "on"
    return bool(default)


@dataclass
class Review:
    findings: list[str] = field(default_factory=list)
    replan_product: str | None = None


def review(rag: WorkerResult | None, db: WorkerResult | None,
           cited_products: Callable[[list[str]], list[str]]) -> Review:
    out = Review()
    rag_payload = rag.payload if rag is not None and isinstance(rag.payload, RagPayload) else None
    published = rag is not None and rag.status in {"completed", "partial"} and \
        rag_payload is not None
    cited: list[str] = []
    if published and rag_payload is not None:
        cited = list(dict.fromkeys(c.doc_id for c in rag_payload.citations))
        if not cited:
            out.findings.append("C1: published answer without citations")
        retrieved = set(rag_payload.retrieved_doc_ids)
        if retrieved and any(c not in retrieved for c in cited):
            out.findings.append("C1: citation outside the retrieved documents")
        if any(not c.quote.strip() for c in rag_payload.citations):
            out.findings.append("C1: citation without quote")
    if db is None or not cited:
        return out
    payload = db.payload if isinstance(db.payload, DbPayload) else None
    unresolved = db.status == "no_data" and db.error is not None and \
        db.error.category == "clarification_required"
    products = cited_products(cited)
    if not products:
        return out
    if unresolved:
        out.findings.append("C2: data product unresolved; cited documents name "
                            + products[0])
        out.replan_product = products[0]
    elif payload is not None and payload.product_id is not None and \
            payload.product_id not in products:
        out.findings.append(f"C2: data product {payload.product_id} differs from the cited "
                            f"documents' products {','.join(products[:3])}")
        if payload.product_source in REPLACEABLE:
            out.replan_product = products[0]
    return out
