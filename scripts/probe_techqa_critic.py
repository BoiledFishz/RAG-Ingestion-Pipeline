"""Replay neutral-ID frozen component inputs; never pass target DOC_ID/answers."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "agentic-rag-homework"))

from agents.critic import LLMCritic  # noqa: E402
from models.llm import MeteredModel, OllamaStructuredModel  # noqa: E402


async def run(output: Path) -> None:
    if await asyncio.to_thread(output.exists):
        raise FileExistsError(output)
    baseline = json.loads((ROOT / "audit/techqa_root_cause_20261003-01/critic_baseline.json")
                          .read_text(encoding="utf-8"))
    meter = MeteredModel(OllamaStructuredModel())
    critic = LLMCritic(meter)
    records = []
    for row in baseline["records"]:
        before = meter.snapshot()
        started = time.perf_counter()
        record = {"id": row["id"], "mode": row["mode"], "baseline": row["critic"]}
        try:
            result = await critic.run(row["query"], row["evidence"], row["diagnosis"],
                                      source_context=row["context"])
            record.update(critic=result.model_dump(), error=None)
        except (ValueError, RuntimeError) as exc:
            record.update(critic=None, error=f"{type(exc).__name__}: {exc}")
        metrics = meter.delta(before)
        metrics.latency_ms = (time.perf_counter() - started) * 1000
        record["metrics"] = metrics.model_dump()
        records.append(record)
        await asyncio.to_thread(output.write_text,
            json.dumps({"complete": False, "records": records}, ensure_ascii=False, indent=2),
            encoding="utf-8")
    await asyncio.to_thread(output.write_text,
        json.dumps({"complete": True, "records": records}, ensure_ascii=False, indent=2),
        encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    asyncio.run(run(parser.parse_args().output))
