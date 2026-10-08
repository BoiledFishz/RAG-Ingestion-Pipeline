"""Subjects and resource permissions originate only in server-owned context."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TrustedContext:
    subject_id: str
    tenant_id: str
    allowed_corpus_scopes: frozenset[str]
    allowed_operations: frozenset[str]

    def permits(self, operation: str, scope: str = "full") -> bool:
        return bool(self.subject_id and self.tenant_id and scope in self.allowed_corpus_scopes
                    and operation in self.allowed_operations)
