"""Freeze retrieval inputs and replay selection; labels/answers never enter prompts."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "enterprise-ai-agent"))

from agents.rag_agent.generation import LLMSelector, grounded_response  # noqa: E402
from models.providers import OllamaStructuredModel  # noqa: E402
from models.schemas import Evidence  # noqa: E402

from rag.techqa.protocol import runtime_protocol  # noqa: E402


async def replay(source: Path, output: Path) -> None:
    await asyncio.to_thread(output.mkdir, parents=True, exist_ok=False)
    protocol = await runtime_protocol()
    protocol["input_path"] = str(await asyncio.to_thread(source.resolve))
    await asyncio.to_thread((output / "protocol.json").write_text,
                            json.dumps(protocol, indent=2), encoding="utf-8")
    rows = json.loads(await asyncio.to_thread(source.read_text, encoding="utf-8"))
    selector = LLMSelector(OllamaStructuredModel("http://localhost:11434", "qwen2.5:7b", 120),
                           fact_audit=True, group_by_document=True)
    results = []
    for row in rows:
        evidence = [Evidence.model_validate(e) for e in row["trace"]["evidence"]]
        start = time.perf_counter()
        item = {"question_id": row["question_id"], "response": None,
                "baseline_status": row["trace"]["status"], "error": None}
        try:
            draft = await selector.select(row["trace"]["original_query"], evidence)
            item.update(draft=draft.model_dump(), response=grounded_response(draft, evidence)
                        .model_dump() if draft.quotes else None)
        except Exception as exc:
            item["error"] = f"{type(exc).__name__}: {exc}"
        item["latency_ms"] = (time.perf_counter() - start) * 1000
        results.append(item)
        await asyncio.to_thread((output / "progress.json").write_text,
            json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        logging.info("%s response=%s error=%s", row["question_id"],
                     item["response"] is not None, item["error"])
    after = await runtime_protocol()
    await asyncio.to_thread((output / "summary.json").write_text,
        json.dumps({"complete": True, "questions": len(results),
                    "protocol_unchanged": protocol["source_sha256"] == after["source_sha256"],
                    "scope": "frozen evidence component; no new retrieval score"}, indent=2),
        encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    logging.basicConfig(level=logging.INFO)
    args = parser.parse_args()
    asyncio.run(replay(args.source, args.output))
