"""Request-scoped authorization for retrieval (decision D3: filter at retrieval time).

The RAG Worker sets the caller's authorized product IDs here; scoped retrievers read it and
never return, rerank or pass to the model a document outside that scope. Unset (None) means
unrestricted and is used only outside requests (offline studies, tests of the bare tool).
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Any

PRODUCT_SCOPE: ContextVar[frozenset[str] | None] = ContextVar("chap12_scope", default=None)
OVERFETCH = 20
OVERFETCH_CAP = 1000


@contextmanager
def product_scope(products: frozenset[str]) -> Iterator[None]:
    token = PRODUCT_SCOPE.set(products)
    try:
        yield
    finally:
        PRODUCT_SCOPE.reset(token)


class DocumentScope:
    """doc_id -> official product IDs of the sample snapshot."""

    def __init__(self, index_path: Path) -> None:
        uri = index_path.resolve().as_uri() + "?mode=ro"
        with sqlite3.connect(uri, uri=True) as db:
            pairs = db.execute("SELECT doc_id, product_id FROM document_products").fetchall()
            docs = [r[0] for r in db.execute("SELECT doc_id FROM technotes")]
        self.products: dict[str, frozenset[str]] = {d: frozenset() for d in docs}
        grouped: dict[str, set[str]] = {}
        for doc_id, product_id in pairs:
            grouped.setdefault(doc_id, set()).add(product_id)
        self.products.update({d: frozenset(p) for d, p in grouped.items()})

    def allowed(self, doc_id: str, scope: frozenset[str] | None) -> bool:
        if scope is None or "*" in scope:
            return True
        return bool(self.products.get(doc_id, frozenset()) & scope)


class ScopedRetriever:
    """Wrap a retriever: over-fetch, then keep only authorized documents, before fusion."""

    def __init__(self, inner: Any, scope: DocumentScope) -> None:
        self.inner, self.scope = inner, scope

    async def retrieve(self, query: str, *, limit: int = 30,
                       filters: dict[str, Any] | None = None) -> list[Any]:
        active = PRODUCT_SCOPE.get()
        if active is None or "*" in active:
            result: list[Any] = await self.inner.retrieve(query, limit=limit, filters=filters)
            return result
        wide = await self.inner.retrieve(query, limit=min(limit * OVERFETCH, OVERFETCH_CAP),
                                         filters=filters)
        kept = [r for r in wide
                if self.scope.allowed(str(r.metadata.get("techqa_document_id")), active)]
        return kept[:limit]
