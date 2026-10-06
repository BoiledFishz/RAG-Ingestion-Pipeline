"""Inference process: receives ONLY query text, never official labels or target IDs."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


async def serve(environment: dict[str, str]) -> None:
    # Clear inherited experimental overrides rather than let them silently affect a run.
    for key in list(os.environ):
        if key.startswith(
            ("TECHQA_", "AGENT_", "RETRIEVAL_", "RRF_", "MAX_CONTEXT_", "MAX_CHUNKS_")
        ):
            del os.environ[key]
    os.environ.update(environment)
    sys.path[:0] = [str(ROOT / "enterprise-ai-agent"), str(ROOT / "src")]
    import httpx
    from agents.rag_agent.factory import build_agent
    from models.schemas import QueryRequest
    from models.settings import Settings

    agent = build_agent(Settings.from_env())
    counters: dict[str, int] = {}
    pipeline: dict[str, Any] = {}
    original_post = httpx.AsyncClient.post

    async def metered_post(self: Any, url: Any, *args: Any, **kwargs: Any) -> Any:
        is_chat = str(url).endswith("/api/chat")
        if is_chat:
            counters["llm_calls"] += 1
        result = await original_post(self, url, *args, **kwargs)
        if is_chat and result.is_success:
            body = result.json()
            for field in ("prompt_eval_count", "eval_count"):
                counters[field] += int(body.get(field, 0))
        return result

    # Transparent cost instrumentation; the request, return value and options are unchanged.
    httpx.AsyncClient.post = metered_post
    original_retrieve = agent.retriever.pipeline.retrieve

    async def observed_retrieve(*args: Any, **kwargs: Any) -> Any:
        outcome = await original_retrieve(*args, **kwargs)
        pipeline.update(
            {
                "candidate_ids": [r.chunk_id for r in outcome.results],
                "reranker_fallback": outcome.diagnostics.reranker_fallback,
            }
        )
        return outcome

    agent.retriever.pipeline.retrieve = observed_retrieve
    while line := await asyncio.to_thread(sys.stdin.readline):
        payload = json.loads(line)
        if set(payload) != {"query"}:
            raise ValueError("Worker refuses IDs, labels, gold answers, or target documents")
        counters.clear()
        counters.update({"llm_calls": 0, "prompt_eval_count": 0, "eval_count": 0})
        pipeline.clear()
        started = time.perf_counter()
        try:
            result = await agent.run(QueryRequest.model_validate(payload))
            output = {"run": result.model_dump(mode="json"), "error": None}
        except Exception as exc:
            logging.exception("Inference failed")
            output = {"run": None, "error": f"{type(exc).__name__}: {exc}"}
        output.update(
            {
                "cost": dict(counters),
                "pipeline": dict(pipeline),
                "wall_latency_ms": (time.perf_counter() - started) * 1000,
            }
        )
        sys.stdout.write(json.dumps(output, ensure_ascii=False) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING, stream=sys.stderr)
    asyncio.run(serve(json.loads(sys.argv[1])))
