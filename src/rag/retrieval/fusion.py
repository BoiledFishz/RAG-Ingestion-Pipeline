"""Rank fusion for heterogeneous retrieval scores."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from collections.abc import Sequence

from rag.retrieval.contracts import SearchResult


def reciprocal_rank_fusion(
    rankings: Sequence[Sequence[SearchResult]],
    *,
    rank_constant: int = 60,
    limit: int = 10,
) -> list[SearchResult]:
    if rank_constant <= 0:
        raise ValueError("rank_constant must be positive")
    scores: defaultdict[str, float] = defaultdict(float)
    representatives: dict[str, SearchResult] = {}
    for ranking in rankings:
        seen_in_ranking: set[str] = set()
        for rank, result in enumerate(ranking, start=1):
            identity = result.chunk_hash or hashlib.sha256(result.text.encode("utf-8")).hexdigest()
            if identity in seen_in_ranking:
                continue
            seen_in_ranking.add(identity)
            scores[identity] += 1.0 / (rank_constant + rank)
            representatives.setdefault(identity, result)
    ordered = sorted(scores, key=scores.__getitem__, reverse=True)[:limit]
    return [representatives[key].with_score(scores[key], backend="hybrid") for key in ordered]
