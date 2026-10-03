"""Replay the new applicability guard on frozen, actual full-corpus Agent outputs.

This isolates the final guard: it is not a fresh retrieval/rewriting benchmark.
Only official user questions and previously selected original evidence reach the LLM.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Any

from pydantic import ValidationError
from rag.techqa.metrics import body_token_f1

from agents.rag_agent.generation import LLMSelector, grounded_response
from agents.rag_agent.service import REFUSAL
from evaluation.evaluate import DEV_PATH, average, checkpoint_protocol, document_id, question_text
from models.errors import InvalidEvidence
from models.providers import OllamaStructuredModel, StructuredModel
from models.schemas import AgentResponse, Evidence, Quotation, SelectionDraft
from models.settings import Settings

LOGGER = logging.getLogger(__name__)


class CountingModel:
    def __init__(self, inner: StructuredModel) -> None:
        self.inner, self.calls = inner, 0

    async def generate(self, prompt: str, schema: dict[str, Any]) -> str:
        self.calls += 1
        return await self.inner.generate(prompt, schema)


async def evaluate(source: Path, output: Path, resume: bool = False) -> dict[str, Any]:
    settings = Settings.from_env()
    source_bytes = await asyncio.to_thread(source.read_bytes)
    original = json.loads(source_bytes)
    questions = json.loads(await asyncio.to_thread(DEV_PATH.read_text, encoding="utf-8"))
    by_id = {row["question_id"]: row for row in original}
    if len(original) != len(questions) or set(by_id) != {r["QUESTION_ID"] for r in questions}:
        raise ValueError("Replay requires one completed record per official development question")
    if any(row["error"] for row in original):
        raise ValueError("Fix baseline execution errors before replaying the answer guard")
    protocol = await asyncio.to_thread(checkpoint_protocol, settings, DEV_PATH)
    protocol.update({"protocol": __doc__,
                     "source_sha256": hashlib.sha256(source_bytes).hexdigest()})
    await asyncio.to_thread(output.mkdir, parents=True, exist_ok=True)
    configuration = output / "run_config.json"
    previous = {}
    progress = output / "progress.jsonl"
    if resume:
        if json.loads(configuration.read_text(encoding="utf-8")) != protocol:
            raise ValueError("Replay source, model, code or settings changed")
        for line in progress.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            previous[row["question_id"]] = row
    else:
        configuration.write_text(json.dumps(protocol, indent=2) + "\n", encoding="utf-8")
        progress.write_text("", encoding="utf-8")
    model = CountingModel(OllamaStructuredModel(
        settings.ollama_url, settings.model, settings.llm_timeout,
    ))
    selector = LLMSelector(model)
    results = []
    for question in questions:
        identifier = question["QUESTION_ID"]
        if identifier in previous and not previous[identifier]["error"]:
            results.append(previous[identifier])
            continue
        baseline = by_id[identifier]
        record = {"question_id": identifier, "answerable": baseline["answerable"],
                  "baseline_status": baseline["trace"]["status"],
                  "baseline_body_f1": baseline["answer_quality"],
                  "original_response": baseline["response"], "model_called": False,
                  "status": baseline["trace"]["status"], "rejected": False, "error": None}
        started = time.perf_counter()
        calls_before = model.calls
        try:
            response = AgentResponse.model_validate(baseline["response"])
            if response.sources:
                allowed = {e["source_id"]: Evidence.model_validate(e)
                           for e in baseline["trace"]["evidence"]}
                evidence = [allowed[source.source_id] for source in response.sources]
                if any(source.quote != allowed[source.source_id].excerpt
                       for source in response.sources):
                    raise ValueError("Baseline answer is not the recorded original excerpt")
                correction = ""
                record["failed_review_attempts"] = []
                for attempt in range(2):
                    try:
                        selected = await selector.review(
                            question_text(question), evidence, correction,
                        )
                        break
                    except (InvalidEvidence, ValidationError) as exc:
                        record["failed_review_attempts"].append(type(exc).__name__)
                        if attempt == 1:
                            raise
                        correction = ("Previous conflict claims failed substring validation. "
                                      "Use only short exact query/source words; do not paraphrase "
                                      "or invent a conflict. If none is explicit, conflicts=[].")
                if selected.sufficient:
                    response = grounded_response(SelectionDraft(quotes=[
                        Quotation(source_id=key, quote=allowed[key].excerpt)
                        for key in dict.fromkeys(selected.source_ids)
                    ]), evidence)
                    record["status"] = "answered"
                else:
                    response = AgentResponse(answer=REFUSAL, sources=[], confidence=0)
                    record.update(status="unanswerable", rejected=True)
            record["response"] = response.model_dump(mode="json")
            cited = any(document_id(s.chunk_id) == question["DOCUMENT"]
                        and f"[{s.source_id}]" in response.answer for s in response.sources)
            record["body_f1"] = (body_token_f1(response.answer, question["ANSWER"]) * cited
                                  if record["answerable"] else None)
        except Exception as exc:
            LOGGER.exception("Applicability review failed for %s", identifier)
            record.update(error=type(exc).__name__, status="review_error", response=None,
                          body_f1=0 if record["answerable"] else None)
        record["review_latency_ms"] = (time.perf_counter() - started) * 1000
        record["model_calls"] = model.calls - calls_before
        record["model_called"] = record["model_calls"] > 0
        results.append(record)
        with progress.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        LOGGER.info("%s (%d/%d) status=%s error=%s", identifier, len(results), len(questions),
                    record["status"], record["error"])
    positives = [r for r in results if r["answerable"]]
    negatives = [r for r in results if not r["answerable"]]
    reviewed = [r for r in results if r["model_called"]]
    summary = {
        "protocol": "Frozen actual retrieval/selection outputs; new final applicability guard only",
        "dataset": "IBM TechQA official development questions", "model": settings.model,
        "questions": len(results), "complete": len(results) == len(questions),
        "model_trials": len(reviewed), "review_rejected_count": sum(r["rejected"] for r in results),
        "model_calls": sum(r["model_calls"] for r in results),
        "baseline_answerable_body_f1": average([r["baseline_body_f1"] or 0 for r in positives]),
        "reviewed_answerable_body_f1": average([r["body_f1"] or 0 for r in positives]),
        "baseline_labelled_refusal_accuracy": average([
            float(r["baseline_status"] == "unanswerable") for r in negatives]),
        "reviewed_labelled_refusal_accuracy": average([
            float(r["status"] == "unanswerable" and not r["error"]) for r in negatives]),
        "answerable_acceptance": average([float(r["status"] == "answered") for r in positives]),
        "average_guard_latency_ms": average([r["review_latency_ms"] for r in reviewed]),
        "error_count": sum(bool(r["error"]) for r in results),
        "limitations": ["No fresh retrieval or query rewriting in this replay",
                        "N labels describe the smaller original candidate pool",
                        "Body F1 and reference document IDs are proxies, not factual accuracy"],
    }
    (output / "runs.json").write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n",
                                      encoding="utf-8")
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    summary = asyncio.run(evaluate(args.input, args.output, args.resume))
    LOGGER.info("Applicability guard summary: %s", summary)
    return int(summary["error_count"] > 0)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    raise SystemExit(main())
