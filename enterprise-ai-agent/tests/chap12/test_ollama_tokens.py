from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from agents.chap12.budget import Budget, BudgetedModel, BudgetLimits, metered
from agents.chap12.ollama_tokens import TokenMeteredOllamaModel, output_budget
from models.errors import DependencyUnavailable


def model(body: dict[str, object], seen: list[dict[str, object]]) -> TokenMeteredOllamaModel:
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        return httpx.Response(200, json=body)

    return TokenMeteredOllamaModel("http://ollama", "qwen2.5:7b",
                                   transport=httpx.MockTransport(handler))


def test_tokens_recorded_and_request_matches_project1() -> None:
    seen: list[dict[str, object]] = []
    budget = Budget(BudgetLimits())
    llm = BudgetedModel(model({"message": {"content": "{}"}, "prompt_eval_count": 120,
                               "eval_count": 30, "done_reason": "stop"}, seen))

    async def go() -> str:
        with metered(budget, "rag"):
            first = await llm.generate("p", {"type": "object"})
            await llm.generate("KIND: FACT_AUDIT\nq", {"type": "object"})
            return first

    assert asyncio.run(go()) == "{}"
    assert (budget.prompt_tokens, budget.completion_tokens, budget.used["llm"]) == (240, 60, 2)
    assert seen[0]["options"] == {"temperature": 0, "num_predict": 300, "num_ctx": 8192}
    assert seen[1]["options"]["num_predict"] == output_budget("KIND: FACT_AUDIT\n") == 900  # type: ignore[index]


def test_missing_counts_stay_null_and_length_stop_fails() -> None:
    budget = Budget(BudgetLimits())
    llm = model({"message": {"content": "{}"}}, [])

    async def go() -> None:
        with metered(budget, "rag"):
            await llm.generate("p", {})

    asyncio.run(go())
    assert budget.prompt_tokens is None and budget.completion_tokens is None
    truncated = model({"message": {"content": "{"}, "done_reason": "length",
                       "prompt_eval_count": 5, "eval_count": 300}, [])
    with pytest.raises(DependencyUnavailable):
        asyncio.run(truncated.generate("p", {}))
