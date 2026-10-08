"""Identity for existing caches, granted by trusted server context only."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from agents.project2.policy import TrustedContext

_IDENTITY: ContextVar[tuple[str, str] | None] = ContextVar("project2_cache_identity", default=None)


def authorization_scope(context: TrustedContext) -> str:
    if not context.permits("rag_explain"):
        raise PermissionError("rag_cache_permission_denied")
    value = {
        "subject": context.subject_id,
        "tenant": context.tenant_id,
        "scopes": sorted(context.allowed_corpus_scopes),
        "operations": sorted(context.allowed_operations),
    }
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def embedding_key(model: str, text: str, data_version: str, scope: str) -> str:
    value = ["project2-existing-cache-v1", model, text, data_version, scope]
    return hashlib.sha256(json.dumps(value, ensure_ascii=False).encode()).hexdigest()


def current_identity() -> tuple[str, str] | None:
    return _IDENTITY.get()


@contextmanager
def cache_context(data_version: str, scope: str | None) -> Iterator[None]:
    # A direct internal caller with no trusted context gets no cache access.
    # This never falls back to the old globally shared user-query cache.
    if scope is not None and (len(scope) != 64 or any(c not in "0123456789abcdef" for c in scope)):
        raise ValueError("Invalid trusted cache scope")
    token = _IDENTITY.set((data_version, scope) if scope is not None else None)
    try:
        yield
    finally:
        _IDENTITY.reset(token)
