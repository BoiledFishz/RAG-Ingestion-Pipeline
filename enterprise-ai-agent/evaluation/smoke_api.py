"""Three real HTTP requests against an already-running Agent API."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
from pathlib import Path

import httpx

from models.schemas import AgentResponse
from models.settings import PROJECT_ROOT

LOGGER = logging.getLogger(__name__)


async def smoke(base_url: str, output: Path) -> None:
    cases = [
        (
            "answerable",
            "User environment variables are not picked up after upgrading Streams 4.1.1.2",
        ),
        ("ambiguous", "权限有问题，怎么办？"),
        ("unanswerable", "How do I repair PostgreSQL XX999?"),
    ]
    observations = []
    async with httpx.AsyncClient(base_url=base_url, timeout=300) as client:
        for category, query in cases:
            response = await client.post("/v1/agent/query", json={"query": query})
            response.raise_for_status()
            validated = AgentResponse.model_validate(response.json())
            assert "charset=utf-8" in response.headers["content-type"].lower()
            if category == "answerable":
                assert validated.sources and validated.confidence > 0
                assert any(s.source_file == "techqa://swg21996508" for s in validated.sources)
                assert "4.1.1.2" in validated.answer and "bashrc" in validated.answer.casefold()
            else:
                assert not validated.sources and validated.confidence == 0
                assert ("补充" if category == "ambiguous" else "无法回答") in validated.answer
            observations.append(
                {
                    "category": category,
                    "query": query,
                    "status_code": response.status_code,
                    "content_type": response.headers["content-type"],
                    "response": validated.model_dump(),
                }
            )
            LOGGER.info("%s HTTP %d passed", category, response.status_code)
    await asyncio.to_thread(output.parent.mkdir, parents=True, exist_ok=True)
    await asyncio.to_thread(
        output.write_text,
        json.dumps(observations, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8001")
    parser.add_argument(
        "--output", type=Path, default=PROJECT_ROOT / "evaluation" / "api_smoke_results.json"
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    asyncio.run(smoke(args.base_url, args.output))
