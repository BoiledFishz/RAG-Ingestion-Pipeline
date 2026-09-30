"""Errors that must not be confused with an unanswerable question."""


class DependencyUnavailable(RuntimeError):
    """Vector store, embedding service or language model is unavailable."""


class InvalidEvidence(ValueError):
    """A model selected a fabricated source or a non-verbatim quotation."""
