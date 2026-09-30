import asyncio

import pytest

from evaluation.factory import model_from_env
from evaluation.run import aggregate, observe, quality
from models.llm import OllamaStructuredModel
from models.schemas import RAGResponse, Source


def test_source_quotes_and_citation_numbers_do_not_score_as_answer():
    response = RAGResponse(
        answer="Use the retrieved checks. [1]", confidence=0.8,
        sources=[Source(document_id="lambda", source="fixture",
                        quote="Lambda supports 1 to 900 seconds.")],
    )
    item = {"answerable": True, "expected": ["1", "900"]}
    assert quality(response, item) == 0
    response.answer = "Lambda supports 1 to 900 seconds. [1]"
    assert quality(response, item) == 1


def test_unknown_question_requires_an_actual_refusal():
    response = RAGResponse(answer="The answer is definitely 42.", confidence=0)
    assert quality(response, {"answerable": False}) == 0
    response.answer = "没有找到足够证据。"
    assert quality(response, {"answerable": False}) == 1


def test_evaluation_keeps_errors_in_denominator():
    async def failing():
        raise TimeoutError("Model timed out")
    row = asyncio.run(observe({"id": "failure"}, failing()))
    result = aggregate("test", [row])
    assert row["error"] == "TimeoutError"
    assert result["answer_quality"] == 0
    assert result["failure_rate"] == 1
    assert result["error_count"] == 1


def test_explicit_real_provider_cannot_silently_use_demo():
    assert isinstance(model_from_env("ollama"), OllamaStructuredModel)
    with pytest.raises(ValueError):
        model_from_env("typo")
