import asyncio
from dataclasses import replace

import pytest

from rag.techqa.data import documents, question_text, questions
from rag.techqa.retrieval import RerankWeights, TechQAReranker, coverage, legacy_chunks


@pytest.mark.parametrize("values", [(float("nan"), .5, .5), (-.1, .6, .5), (.5, .5, .5)])
def test_invalid_weights_fail_at_configuration(values):
    with pytest.raises(ValueError, match="sum to one"):
        RerankWeights(*values)


def test_default_score_and_instrumentation_remain_identical(monkeypatch):
    monkeypatch.delenv("TECHQA_RERANK_WEIGHTS", raising=False)
    row = questions("fixture")[0]
    doc = next(d for d in documents("fixture") if d["id"] == row["DOCUMENT"])
    chunks = legacy_chunks(doc)[:2]
    candidates = [replace(c, metadata={**c.metadata, "bm25_document_rank": i})
                  for i, c in enumerate(chunks, 1)]
    query = question_text(row)
    reranker = TechQAReranker()

    async def fixed_vectors(texts):
        # A provider double tests weight arithmetic, not retrieval quality.
        return [[1.0, 0.0] for _ in texts]

    reranker.embeddings = fixed_vectors
    scores = {}
    output = asyncio.run(reranker.rerank(query, candidates, components=scores))
    for candidate in candidates:
        lexical = coverage(query, str(candidate.metadata["context_summary"]) + " "
                           + candidate.text)
        prior = 1 / (1 + int(candidate.metadata["bm25_document_rank"]) / 5)
        assert scores[candidate.chunk_id]["total_score"] == .5 + .3 * lexical + .2 * prior
    assert output == asyncio.run(reranker.rerank(query, candidates))


def test_env_profile_and_legacy_lexical_profile(monkeypatch):
    monkeypatch.delenv("TECHQA_RERANK_WEIGHTS", raising=False)
    assert TechQAReranker().weights == RerankWeights(.5, .3, .2)
    assert TechQAReranker(False).weights == RerankWeights(0, .55, .45)
    monkeypatch.setenv("TECHQA_RERANK_WEIGHTS", "0.7,0.2,0.1")
    assert TechQAReranker().weights == RerankWeights(.7, .2, .1)
