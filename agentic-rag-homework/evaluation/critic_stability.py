"""Repeated Diagnosis/Critic trials on unchanged official TechQA reference evidence.

This is a component stability check, not a retrieval or answer-quality benchmark.
Every retry and failure remains in the result; successful fallbacks never count as passes.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from rag.techqa.data import question_text, questions
from rag.techqa.metrics import body_token_f1
from rag.techqa.retrieval import open_index

from agents.critic import CriticLoop, LLMCritic, LLMGroundedDiagnosisAgent
from agents.rag_agent.service import ContextCompressor
from models.llm import MeteredModel, OllamaStructuredModel
from vectorstore.techqa import TechQAStore

LOGGER = logging.getLogger(__name__)


async def evaluate(
    limit: int, repeats: int, output: Path, cpu: bool, evidence_mode: str = "reference",
    split: str = "train", label: str = "Y",
) -> dict[str, Any]:
    rows = [r for r in questions(split) if label == "all" or r["ANSWERABLE"] == label][:limit]
    if not rows or repeats < 1:
        raise ValueError("Select at least one official question and repetition")
    await asyncio.to_thread(output.mkdir, parents=True, exist_ok=True)
    observations = []
    reference_index = open_index()
    store = TechQAStore() if evidence_mode == "retrieved" else None
    model_name = ""
    with (output / "runs.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            document = reference_index.get(str(row["DOCUMENT"]))
            if document is None:
                if row["ANSWERABLE"] == "Y":
                    raise ValueError("Official reference document is unavailable")
            if store:
                # Neither DOCUMENT, ANSWER nor DOC_IDS is input to retrieval/compression.
                candidates = await store.search(question_text(row), top_k=20)
                compressed = ContextCompressor(max_sources=12).compress(
                    question_text(row), candidates,
                )
                evidence_map = {str(i): doc.document_id
                                for i, (doc, _, _) in enumerate(compressed, 1)}
                evidence = "\n".join(f"[{i}] {text}"
                                     for i, (_, text, _) in enumerate(compressed, 1))
                context = {str(i): {"title": doc.title[:200], "applicability": doc.text[:500]}
                           for i, (doc, _, _) in enumerate(compressed, 1)}
            else:
                if row["ANSWERABLE"] != "Y":
                    raise ValueError("Reference evidence mode requires answerable questions")
                assert document is not None
                evidence, evidence_map = "[1] " + row["ANSWER"], {"1": row["DOCUMENT"]}
                context = {"1": {"title": document["title"][:200],
                                  "applicability": document["text"][:500]}}
            for repetition in range(1, repeats + 1):
                if not evidence:
                    item: dict[str, Any] = {"id": row["QUESTION_ID"], "repetition": repetition,
                            "answerable": row["ANSWERABLE"] == "Y",
                            "document_id": row["DOCUMENT"], "evidence_documents": {},
                            "body_f1": 0, "status": "skipped_no_evidence", "run": None}
                    observations.append(item)
                    handle.write(json.dumps(item, ensure_ascii=False) + "\n")
                    handle.flush()
                    LOGGER.warning("%s repeat=%d no evidence; Critic was not called",
                                   row["QUESTION_ID"], repetition)
                    continue
                model = OllamaStructuredModel(num_gpu=0 if cpu else None)
                model_name = model.model
                meter = MeteredModel(model)
                run = await CriticLoop(
                    LLMGroundedDiagnosisAgent(meter), LLMCritic(meter), meter,
                ).run(question_text(row), evidence, source_context=context)
                correct_citation = any(
                    key == str(row["DOCUMENT"]) and f"[{identifier}]" in run.final_diagnosis
                    for identifier, key in evidence_map.items()
                )
                item = {"id": row["QUESTION_ID"], "repetition": repetition,
                        "answerable": row["ANSWERABLE"] == "Y",
                        "document_id": row["DOCUMENT"], "evidence_documents": evidence_map,
                        "body_f1": body_token_f1(run.final_diagnosis, row["ANSWER"])
                        * correct_citation if run.answer_sufficient else 0,
                        "status": "reviewed", "run": run.model_dump(mode="json")}
                observations.append(item)
                handle.write(json.dumps(item, ensure_ascii=False) + "\n")
                handle.flush()
                LOGGER.info("%s repeat=%d passed=%s retries=%d", row["QUESTION_ID"],
                            repetition, run.passed, run.retries)
    summary = summarize(observations, rows, repeats, evidence_mode, split, model_name)
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def summarize(observations: list[dict[str, Any]], rows: list[dict[str, Any]], repeats: int,
              evidence_mode: str, split: str, model_name: str) -> dict[str, Any]:
    """Missing evidence stays in quality denominators, never a fabricated Critic pass.

    The shared retriever can hide a failed branch behind an empty result, so skipped
    cases conservatively earn no labelled-refusal credit either.
    """
    reviewed = [r for r in observations if r["run"] is not None]
    count = len(reviewed)
    reviewed_ids = {r["id"] for r in reviewed}
    reviewed_rows = [row for row in rows if row["QUESTION_ID"] in reviewed_ids]
    denominator = max(count, 1)
    summary = {
        "dataset": f"IBM TechQA official {split} questions",
        "protocol": ("oracle reference evidence; repeated component checks, no retrieval"
                     if evidence_mode == "reference" else
                     "open full-corpus retrieval; fixed retrieved evidence per question; "
                     "no reference answers or DOC_IDS supplied to retrieval or agents"),
        "evidence_mode": evidence_mode,
        "model": model_name, "questions": len(rows), "repeats": repeats,
        "trials": len(observations), "model_trials": count,
        "skipped_no_evidence": len(observations) - count,
        "skipped_answerable_trials": sum(r["answerable"] for r in observations
                                         if r["run"] is None),
        "complete": len(observations) == len(rows) * repeats,
        "pass_rate": sum(r["run"]["passed"] for r in reviewed) / denominator,
        "answer_acceptance": sum(r["run"]["answer_sufficient"] for r in reviewed) / denominator,
        "protocol_consistency": sum(
            len({r["run"]["passed"] for r in reviewed if r["id"] == row["QUESTION_ID"]}) == 1
            for row in reviewed_rows
        ) / max(len(reviewed_rows), 1),
        "sufficiency_consistency": sum(
            len({r["run"]["answer_sufficient"] for r in reviewed
                 if r["id"] == row["QUESTION_ID"]}) == 1
            for row in reviewed_rows
        ) / max(len(reviewed_rows), 1),
        "diagnosis_consistency": sum(
            len({r["run"]["final_diagnosis"] for r in reviewed
                 if r["id"] == row["QUESTION_ID"]}) == 1
            for row in reviewed_rows
        ) / max(len(reviewed_rows), 1),
        "first_attempt_pass_rate": sum(r["run"]["attempts"][0]["critique"]["passed"]
                                       for r in reviewed) / denominator,
        "failed_trials": sum(not r["run"]["passed"] for r in reviewed),
        "average_retries": sum(r["run"]["retries"] for r in reviewed) / denominator,
        "model_errors": sum(r["run"]["metrics"]["model_errors"] for r in reviewed),
        "answerable_body_f1": sum(r["body_f1"] for r in observations if r["answerable"])
        / max(sum(r["answerable"] for r in observations), 1),
        "answerable_acceptance": sum(r["run"]["answer_sufficient"] for r in reviewed
                                     if r["answerable"])
        / max(sum(r["answerable"] for r in observations), 1),
        "labelled_refusal_accuracy": (sum(r["run"]["passed"] and not r["run"]["answer_sufficient"]
                                          for r in reviewed if not r["answerable"])
                                      / sum(not r["answerable"] for r in observations))
        if any(not r["answerable"] for r in observations) else None,
    }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--cpu", action="store_true")
    parser.add_argument("--evidence-mode", choices=["reference", "retrieved"], default="reference")
    parser.add_argument("--split", choices=["train", "dev", "fixture"], default="train")
    parser.add_argument("--label", choices=["Y", "N", "all"], default="Y")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.limit < 1 or args.repeats < 1:
        parser.error("--limit and --repeats must be positive")
    summary = asyncio.run(evaluate(args.limit, args.repeats, args.output, args.cpu,
                                  args.evidence_mode, args.split, args.label))
    LOGGER.info("Critic component summary: %s", summary)
    return int(summary["failed_trials"] > 0 or summary["sufficiency_consistency"] < 1
               or summary["model_trials"] == 0 or summary["skipped_answerable_trials"] > 0)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    raise SystemExit(main())
