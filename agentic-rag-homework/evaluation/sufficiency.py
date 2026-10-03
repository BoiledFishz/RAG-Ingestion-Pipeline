"""Answer-sufficiency challenge on official N candidate pools, no invented negatives.

This evaluates the evidence selector alone, not full-corpus retrieval. N labels
refer to these DOC_IDS, although documents may still contradict the annotations.
Use train for development, and keep dev labels out of threshold calibration.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
from pathlib import Path

from rag.techqa.data import question_text, questions
from rag.techqa.retrieval import coverage, open_index

from agents.rag_agent.service import REFUSAL, GroundedAnswerer
from models.llm import MeteredModel, OllamaStructuredModel
from vectorstore.techqa import TechQAStore

LOGGER = logging.getLogger(__name__)


async def evaluate(split: str, limit: int, output: Path, cpu: bool, label: str = "N") -> None:
    index = open_index()
    rows = [r for r in questions(split) if r["ANSWERABLE"] == label][:limit or None]
    if not rows:
        raise ValueError("No official questions match the selected split and label")
    observations = []
    await asyncio.to_thread(output.mkdir, parents=True, exist_ok=True)
    with (output / "runs.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            query = question_text(row)
            docs = [doc for key in row["DOC_IDS"] if (doc := index.get(str(key)))]
            candidates = [TechQAStore.convert(doc, coverage(query, doc["title"] + doc["text"]))
                          for doc in docs]
            candidates.sort(key=lambda doc: doc.score, reverse=True)
            backend = OllamaStructuredModel(num_gpu=0 if cpu else None)
            model = MeteredModel(backend)
            answer = await GroundedAnswerer(model).answer(query, candidates)
            record = {
                "id": row["QUESTION_ID"], "candidate_ids": row["DOC_IDS"],
                "available_documents": len(docs), "response": answer.model_dump(),
                "refused": answer.answer == REFUSAL and not answer.sources,
                "answered": bool(answer.sources),
                "model_errors": model.metrics.model_errors,
                "selector_outputs": model.outputs,
                "correct_document": any(s.document_id == row["DOCUMENT"] for s in answer.sources)
                if label == "Y" else None,
            }
            observations.append(record)
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            handle.flush()
            LOGGER.info("%s refused=%s model_errors=%s (%d/%d)", record["id"],
                        record["refused"], record["model_errors"], len(observations), len(rows))
    summary = {
        "split": split, "questions": len(rows), "corpus": index.manifest,
        "label": label,
        "protocol": "Evidence-selector proxy restricted to official DOC_IDS; "
        "annotations may conflict with document facts; not an end-to-end retrieval score",
        "provider": "Ollama " + backend.model, "device": "cpu" if cpu else "default",
        "refusal_accuracy": sum(r["refused"] for r in observations) / max(len(rows), 1)
        if label == "N" else None,
        "answer_acceptance": sum(r["answered"] for r in observations) / max(len(rows), 1),
        "correct_document_rate": sum(bool(r["correct_document"]) for r in observations)
        / max(len(rows), 1) if label == "Y" else None,
        "model_errors": sum(r["model_errors"] for r in observations),
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    LOGGER.info("Summary: %s", summary)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=["train", "dev"], default="train")
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--cpu", action="store_true")
    parser.add_argument("--label", choices=["N", "Y"], default="N")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.limit < 0:
        parser.error("--limit must be nonnegative")
    asyncio.run(evaluate(args.split, args.limit, args.output, args.cpu, args.label))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    main()
