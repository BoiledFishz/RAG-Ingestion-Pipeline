import asyncio

import pytest
from rag.techqa.data import questions

from evaluation.factory import model_from_env
from evaluation.run import aggregate, observe, quality
from models.llm import OllamaStructuredModel
from models.schemas import RAGResponse, Source


def test_source_quotes_and_citation_numbers_do_not_score_as_answer():
    original = questions("fixture")[0]
    response = RAGResponse(
        answer="[1]", confidence=0.8,
        sources=[Source(document_id=original["DOCUMENT"], source="techqa://swg21996508",
                        quote=original["ANSWER"])],
    )
    item = {"answerable": True, "ground_truth": original["ANSWER"],
            "expected_document": original["DOCUMENT"]}
    assert quality(response, item) == 0
    response.answer = original["ANSWER"] + " [1]"
    assert quality(response, item) == 1
    response.answer = original["ANSWER"] + " [7]"
    assert quality(response, item) == 0


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


def test_refusals_do_not_hide_low_answerable_body_quality():
    original = questions("fixture")
    rows = [
        {"id": original[0]["QUESTION_ID"], "answerable": True, "quality": 0,
         "error": None, "run": None, "metrics": {
             "llm_calls": 1, "tool_calls": 1, "input_tokens": 1,
             "output_tokens": 1, "latency_ms": 1}},
        {"id": next(q["QUESTION_ID"] for q in original if q["ANSWERABLE"] == "N"),
         "answerable": False, "quality": 1, "error": None, "run": None, "metrics": {
             "llm_calls": 1, "tool_calls": 1, "input_tokens": 1,
             "output_tokens": 1, "latency_ms": 1}},
    ]
    result = aggregate("test", rows)
    assert result["answer_quality"] == 0.5
    assert result["answerable_body_f1"] == 0
    assert result["labelled_refusal_accuracy"] == 1
