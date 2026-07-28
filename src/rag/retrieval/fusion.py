"""Hand-written Reciprocal Rank Fusion with chunk-level deduplication."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import replace

from rag.retrieval.contracts import SearchResult


def _identity(result: SearchResult) -> str:
    return result.chunk_id or hashlib.sha256(result.text.encode("utf-8")).hexdigest()


def deduplicate_by_chunk_id(results: Sequence[SearchResult]) -> list[SearchResult]:
    unique: dict[str, SearchResult] = {}
    for result in results:
        unique.setdefault(_identity(result), result)
    return list(unique.values())


def reciprocal_rank_fusion(
    rankings: Sequence[Sequence[SearchResult]],
    *,
    rank_constant: int = 60,
    limit: int = 10,
) -> list[SearchResult]:
    """Compute RRF(d) = sum_r 1 / (rank_constant + rank_r(d))."""

    if rank_constant <= 0:
        raise ValueError("rank_constant must be positive")
    if limit <= 0:
        return []

    scores: defaultdict[str, float] = defaultdict(float)
    representatives: dict[str, SearchResult] = {}
    dense_ranks: dict[str, int] = {}
    sparse_ranks: dict[str, int] = {}
    sources: defaultdict[str, set[str]] = defaultdict(set)

    for ranking in rankings:
        seen_in_ranking: set[str] = set()
        for rank, result in enumerate(ranking, start=1):
            identity = _identity(result)
            if identity in seen_in_ranking:
                continue
            seen_in_ranking.add(identity)
            scores[identity] += 1.0 / (rank_constant + rank)
            representatives.setdefault(identity, result)

            result_sources = result.retrieval_sources or (result.backend,)
            sources[identity].update(result_sources)
            if "dense" in result_sources or result.backend == "dense":
                dense_ranks.setdefault(identity, result.dense_rank or rank)
            if "sparse" in result_sources or result.backend == "sparse":
                sparse_ranks.setdefault(identity, result.sparse_rank or rank)

    ordered = sorted(scores, key=lambda key: (-scores[key], key))[:limit]
    fused: list[SearchResult] = []
    for fusion_rank, identity in enumerate(ordered, start=1):
        representative = representatives[identity]
        score = scores[identity]
        fused.append(
            replace(
                representative,
                score=score,
                backend="hybrid",
                retrieval_rank=fusion_rank,
                retrieval_score=score,
                dense_rank=dense_ranks.get(identity),
                sparse_rank=sparse_ranks.get(identity),
                fusion_rank=fusion_rank,
                retrieval_sources=tuple(sorted(sources[identity])),
            )
        )
    return fused
