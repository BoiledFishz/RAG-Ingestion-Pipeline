"""Score-independent relevance gate for a failed reranker; never changes ordering."""

from __future__ import annotations

from rag.retrieval.contracts import SearchResult
from rag.retrieval.sparse import BM25Retriever

_STOPWORDS = frozenset(
    "a an the is are was were be been do does did how what which why when where "
    "should can could would for of to and or in on with it its that this".split()
)


def query_coverage(query: str, result: SearchResult) -> float:
    """Fraction of meaningful query terms supported by the candidate text/summary."""
    terms = set(BM25Retriever.tokenize(query)) - _STOPWORDS
    evidence = set(BM25Retriever.tokenize(
        f"{result.text}\n{result.metadata.get('context_summary', '')}"
    ))
    return len(terms & evidence) / len(terms) if terms else 0.0
