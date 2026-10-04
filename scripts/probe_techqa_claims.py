"""Audit preserved native bad claims without retrieving again or using gold answers."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

from rag.techqa.claims import Claim, ComposedAnswer, audit_claims
from rag.techqa.data import question_text, questions

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "agentic-rag-homework"))
from models.llm import MeteredModel, OllamaStructuredModel  # noqa: E402


async def run(output: Path) -> None:
    if await asyncio.to_thread(output.exists):
        raise FileExistsError(output)
    source = ROOT / "enterprise-ai-agent/evaluation/results/techqa_quality_pilot_20261003-02"
    rows = [json.loads(line) for line in (source / "progress.jsonl")
            .read_text(encoding="utf-8").splitlines()]
    by_id = {r["QUESTION_ID"]: r for r in questions("dev")}
    meter = MeteredModel(OllamaStructuredModel())
    records = []
    for row in rows[:2]:
        sources = {s["source_id"]: s["quote"] for s in row["response"]["sources"]}
        claims = []
        for line in row["response"]["answer"].splitlines()[1:]:
            text, key = line.rsplit(" [", 1)
            claims.append(Claim(text=text, source_id=key[:-1], exact_quote=sources[key[:-1]]))
        answer = ComposedAnswer(claims=claims, status="partial",
            covered_facts=row["trace"]["covered_facts"],
            missing_facts=row["trace"]["missing_facts"])
        context = {e["source_id"]: {"title": e["title"], "applicability": e["applicability"]}
                   for e in row["trace"]["evidence"] if e["source_id"] in sources}
        before, started = meter.snapshot(), time.perf_counter()
        record = {"id": row["question_id"]}
        try:
            await audit_claims(meter, question_text(by_id[row["question_id"]]),
                               answer, sources, context)
            record.update(rejected=False, error=None)
        except ValueError as exc:
            record.update(rejected=True, error=str(exc))
        metric = meter.delta(before)
        metric.latency_ms = (time.perf_counter() - started) * 1000
        record.update(metrics=metric.model_dump(), raw_output=meter.outputs[-1])
        records.append(record)
    await asyncio.to_thread(output.write_text,
        json.dumps({"complete": True, "records": records}, ensure_ascii=False, indent=2),
        encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    asyncio.run(run(parser.parse_args().output))
