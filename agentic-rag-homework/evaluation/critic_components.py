"""Controlled corruptions of real TechQA evidence; never a replacement gold set.

Expected labels are engineering/AI-assisted component annotations, not independent
human factual ratings. The unchanged official questions/documents are saved with
every mutation. Source IDs are neutral; DOC_ID and reference answers are not inputs.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
from pathlib import Path
from typing import Any

from rag.techqa.data import question_text, questions
from rag.techqa.evidence import aspect_passages
from rag.techqa.protocol import runtime_protocol

from agents.critic import CriticLoop, LLMCritic, LLMGroundedDiagnosisAgent
from models.llm import MeteredModel, OllamaStructuredModel
from models.schemas import CriticIssue

ROOT = Path(__file__).resolve().parents[2]
LOGGER = logging.getLogger(__name__)


def cases() -> list[dict[str, Any]]:
    source = ROOT / "audit/techqa_root_cause_20261003-01"
    parents = {key: json.loads((source / f"{key}.json").read_text(encoding="utf-8"))
               for key in ["TRAIN_Q006", "TRAIN_Q007", "TRAIN_Q011"]}
    baseline = json.loads((source / "critic_baseline.json").read_text(encoding="utf-8"))
    lookup = next(r for r in baseline["records"] if r["id"] == "TRAIN_Q011"
                  and r["mode"] == "actual_selected_blocks")
    rows = {r["QUESTION_ID"]: r for r in questions("fixture")}
    originals = {}
    for key, record in parents.items():
        query = question_text(rows[key])
        spans = aspect_passages(query, record["frozen_parent"]["text"])
        originals[key] = "\n\n".join(p.text for p in spans)
    security, credentials, procedure = (originals[k] for k in
                                       ["TRAIN_Q006", "TRAIN_Q007", "TRAIN_Q011"])
    parent = parents["TRAIN_Q007"]["frozen_parent"]["text"]
    symptom = parent[parent.index("SYMPTOM"):parent.index("CAUSE")].strip()
    final_step = "6. License your IBM SPSS Statistics product."
    assert final_step in procedure
    condition = next(line for line in security.splitlines() if "Huawei MTOSI Collector" in line)

    def item(name: str, key: str, answer: str, evidence: str, valid: bool,
             defect: str = "", *, title_only: bool = False) -> dict[str, Any]:
        record = parents[key]
        return {"case": name, "question_id": key,
                "query": rows[key]["QUESTION_TITLE"] if title_only else question_text(rows[key]),
                "input_view": "official title only" if title_only else "official title and body",
                "answer": answer, "evidence": evidence, "expected_valid": valid,
                "known_defect": defect, "source_parent_sha256": record["frozen_parent"]["sha256"],
                "annotation": "engineering/AI-assisted controlled mutation; not human audit"}

    return [
        item("correct_answer", "TRAIN_Q006", security + " [1]", "[1] " + security, True),
        item("missing_last_step", "TRAIN_Q011", procedure.replace(final_step, "") + " [1]",
             "[1] " + procedure, False, "Chosen licensing procedure omits its last step"),
        item("missing_exposure_condition", "TRAIN_Q006",
             security.replace(condition, "IBM Tivoli Network Manager IP Edition 4.1.1 & 4.2.0")
             + " [1]", "[1] " + security, False,
             "Affected versions are conditional on Huawei MTOSI Collector installation"),
        item("adjacent_version", "TRAIN_Q011",
             procedure.replace("root:admin 25", "root:admin 20") + " [1]",
             "[1] " + procedure, False, "Release 25 command changed to Release 20"),
        item("wrong_operation", "TRAIN_Q011", lookup["evidence"][4:] + " [2]",
             "[1] " + procedure + "\n[2] " + lookup["evidence"][4:], False,
             "Getting a code again does not apply the already-owned activation code"),
        item("wrong_component", "TRAIN_Q007",
             credentials.replace("component-managed", "container-managed")
             .replace("-componentAuthAlias", "-containerAuthAlias") + " [1]",
             "[1] " + credentials, False,
             "Component credential selection and its argument changed to container selection"),
        item("symptom_without_solution", "TRAIN_Q007", symptom + " [1]",
             "[1] " + credentials, False, "Symptom only; credential configuration absent"),
        item("licensing_for_installation_title", "TRAIN_Q011",
             lookup["evidence"][4:] + " [1]", "[1] " + procedure, False,
             "Official title-only request asks to load the product, not retrieve an existing key",
             title_only=True),
        item("supported_refusal", "TRAIN_Q006", "证据不足，无法给出可靠诊断。 [1]",
             "[1] " + security, False, "Complete vulnerability evidence incorrectly refused"),
        item("insufficient_evidence_refusal", "TRAIN_Q007", "证据不足，无法给出可靠诊断。 [1]",
             "[1] " + symptom, True),
    ]


class InjectedDiagnosis:
    """Inject one known component corruption, then permit evidence-based repair."""

    def __init__(self, answer: str, model: MeteredModel) -> None:
        self.initial = answer
        self.used = False
        self.inner = LLMGroundedDiagnosisAgent(model, controlled=True)

    async def run(self, task: str, evidence: str, previous: str = "",
                  feedback: list[CriticIssue] | None = None,
                  source_context: dict[str, dict[str, str]] | None = None) -> str:
        if not self.used:
            self.used = True
            return self.initial
        return await self.inner.run(task, evidence, previous, feedback, source_context)


async def evaluate(output: Path, versions: list[str] | None = None,
                   selected_cases: list[str] | None = None) -> dict[str, Any]:
    await asyncio.to_thread(output.mkdir, parents=True, exist_ok=False)
    versions = versions or ["no_critic", "legacy_critic", "improved_critic"]
    protocol = await runtime_protocol()
    settings = {"versions": versions, "selected_cases": selected_cases,
                "repair_generation": "controlled",
                "max_retries": 2, "scope": "frozen actual-source component corruptions"}
    protocol["benchmark_settings"] = settings
    await asyncio.to_thread((output / "protocol.json").write_text,
                            json.dumps(protocol, indent=2), encoding="utf-8")
    fixtures = cases()
    if selected_cases:
        unknown = set(selected_cases) - {case["case"] for case in fixtures}
        if unknown:
            raise ValueError("Unknown component cases: " + ", ".join(sorted(unknown)))
        fixtures = [case for case in fixtures if case["case"] in selected_cases]
    await asyncio.to_thread((output / "cases.json").write_text,
        json.dumps(fixtures, ensure_ascii=False, indent=2), encoding="utf-8")
    observations = []
    for case in fixtures:
        for version in versions:
            record = {"case": case["case"], "version": version,
                      "expected_valid": case["expected_valid"], "run": None}
            if version == "no_critic":
                record.update(initial_accepted=True, final_accepted=True, calls=0, tokens=0,
                              retries=0, latency_ms=0, error=False)
            else:
                meter = MeteredModel(OllamaStructuredModel())
                run = await CriticLoop(InjectedDiagnosis(case["answer"], meter),
                    LLMCritic(meter, fact_audit=version == "improved_critic"), meter).run(
                        case["query"], case["evidence"])
                record.update(initial_accepted=run.attempts[0].critique.passed,
                    final_accepted=run.passed, calls=run.metrics.llm_calls,
                    tokens=run.metrics.input_tokens + run.metrics.output_tokens,
                    retries=run.retries, latency_ms=run.metrics.latency_ms,
                    error=any(i.code in {"invalid_model_output", "model_unavailable"}
                              for a in run.attempts for i in a.critique.issues),
                    raw_model_outputs=meter.outputs,
                    run=run.model_dump(mode="json"))
            observations.append(record)
            await asyncio.to_thread((output / "progress.json").write_text,
                json.dumps(observations, ensure_ascii=False, indent=2), encoding="utf-8")
            LOGGER.info("%s %s initial_accepted=%s", case["case"], version,
                        record["initial_accepted"])
    summary = {}
    for version in versions:
        group = [r for r in observations if r["version"] == version]
        faulty = [r for r in group if not r["expected_valid"]]
        valid = [r for r in group if r["expected_valid"]]
        summary[version] = {
            "defect_recall": sum(not r["initial_accepted"] for r in faulty) / len(faulty)
                             if faulty else None,
            "false_accept_rate": sum(r["initial_accepted"] for r in faulty) / len(faulty)
                                 if faulty else None,
            "false_reject_rate": sum(not r["initial_accepted"] for r in valid) / len(valid)
                                 if valid else None,
            "average_retry": sum(r["retries"] for r in group) / len(group),
            "llm_calls": sum(r["calls"] for r in group) / len(group),
            "tokens": sum(r["tokens"] for r in group) / len(group),
            "latency_ms": sum(r["latency_ms"] for r in group) / len(group),
            "protocol_error_cases": sum(r["error"] for r in group),
            # These require external factual adjudication of every repair; do not
            # substitute Critic pass or exact-quote protocol checks for truth.
            "issue_repair_rate": None, "new_issue_rate": None, "final_fact_coverage": None,
        }
    result = {"complete": True, "cases": len(fixtures), "observations": len(observations),
              "protocol": "controlled real-source corruptions; engineering/AI-assisted labels",
              "dataset_sha256": hashlib.sha256(json.dumps(fixtures, sort_keys=True).encode())
                                .hexdigest(), "summary": summary}
    after = await runtime_protocol()
    after["benchmark_settings"] = settings
    result["protocol_unchanged"] = protocol == after
    await asyncio.to_thread((output / "summary.json").write_text,
                            json.dumps(result, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--versions", nargs="+",
                        choices=["no_critic", "legacy_critic", "improved_critic"])
    parser.add_argument("--cases", nargs="+")
    logging.basicConfig(level=logging.INFO)
    args = parser.parse_args()
    asyncio.run(evaluate(args.output, args.versions, args.cases))
