"""Human-authorized single-fact supplement; frozen v0 native evaluator stays unchanged."""

from __future__ import annotations

import argparse
import hashlib
import logging
import re
from pathlib import Path
from typing import Any

from evaluation_protocol import review
from evaluation_protocol.annotations import approved_definitions, validate_human_ratings
from evaluation_protocol.statistics import metric
from evaluation_protocol.storage import ROOT, STATE, digest, read, verify, write_new

LOGGER = logging.getLogger(__name__)
POLICY = STATE / "annotation_policy.a1.json"


def load_policy() -> dict[str, Any]:
    verify(POLICY)
    snapshot_path = STATE / "annotation_a1.snapshot.json"
    verify(snapshot_path)
    snapshot = read(snapshot_path)
    if any(digest(ROOT / name) != sha for name, sha in snapshot["files"].items()):
        raise ValueError("A1 annotation implementation/document changed after freezing")
    original_path = STATE / "baseline_v0.evaluator_snapshot.json"
    verify(original_path)
    if digest(original_path) != snapshot["baseline_v0_evaluator_snapshot_sha256"]:
        raise ValueError("Frozen v0 evaluator provenance changed")
    original = read(original_path)
    if any(digest(ROOT / name) != sha for name, sha in original["files"].items()):
        raise ValueError("Reused v0 evaluation code changed")
    policy: dict[str, Any] = read(POLICY)
    if policy["human_authorization"] != "允许补充协议，单独报告":
        raise ValueError("Human authorization for A1 missing")
    return policy


def freeze_facts(path: Path) -> None:
    """Approve reference definitions only after the named human has signed each item."""
    load_policy()
    value = read(path)
    partition = value["partition"]
    if partition not in {"tune", "held-out"}:
        raise ValueError("Unknown partition")
    if not value.get("is_human") or not str(value.get("annotator") or "").strip():
        raise ValueError("Named human reference reviewer required")
    draft = STATE / f"facts_{partition}.draft.json"
    verify(draft)
    originals = {r["question_id"]: r for r in read(draft)["items"]}
    approved: list[dict[str, Any]] = []
    for row in value["items"]:
        original = originals[row["question_id"]]
        if (
            row["question"] != original["question"]
            or row["official_answer"] != original["official_answer"]
        ):
            raise ValueError("Official question/answer modified")
        if row.get("human_approved") is not True:
            continue
        facts = row["required_facts"]
        single = len(facts) == 1
        if single:
            reason = row.get("review_note") or row.get("exception")
            if not row.get("fact_count_exception", {}).get("proposed") or not reason:
                raise ValueError("Single-fact exception needs an explicit human-reviewed reason")
        elif not 2 <= len(facts) <= 5:
            raise ValueError(
                "Require 2-5 facts, or a justified single-fact exception; zero facts invalid"
            )
        quotes = [f["reference_quote"] for f in facts]
        if any(i != j and a in b for i, a in enumerate(quotes) for j, b in enumerate(quotes)):
            raise ValueError("Duplicate or contained required facts")
        for index, fact in enumerate(facts, 1):
            if (
                fact["fact_id"] != f"F{index}"
                or not fact["text"].strip()
                or not fact["reference_quote"]
                or fact["reference_quote"] not in original["official_answer"]
            ):
                raise ValueError("Each fact requires an exact official-answer reference quote")
            if fact["category"] not in {"version", "step", "command", "condition", "other"}:
                raise ValueError("Invalid fact category")
        row["annotator"] = value["annotator"]
        row["definition_status"] = "human_verified_reference_only"
        row["fact_count_exception"] = {
            "proposed": single,
            "human_authorized": single,
            "reason": (row.get("review_note") or row.get("exception")) if single else None,
            "formal_metric_policy": "separate descriptive report; exclude main coverage"
            if single
            else None,
        }
        approved.append(row)
    if not approved or len({r["question_id"] for r in approved}) != len(approved):
        raise ValueError("No approved facts or duplicate definitions")
    write_new(
        STATE / f"facts_{partition}.human_frozen.json",
        {
            "partition": partition,
            "annotator": value["annotator"],
            "is_human": True,
            "status": "human_verified",
            "items": approved,
            "unreviewed_questions": len(originals) - len(approved),
            "reviewed_without_model_answers": True,
            "draft_sha256": digest(draft),
            "annotation_policy": "A1",
            "annotation_policy_sha256": digest(POLICY),
        },
    )


def summarize_scores(
    rows: list[dict[str, Any]],
    payloads: dict[str, dict[str, Any]],
    definitions: dict[str, Any],
) -> dict[str, Any]:
    """Pure post-inference scoring; keep exception denominators and disagreements visible."""
    facts = {r["question_id"]: r for r in definitions["items"]}
    ratings = {
        name: {(r["question_id"], r["answer_sha256"]): r for r in p["items"]}
        for name, p in payloads.items()
    }
    scored, pairs = [], []
    disagreements = {}
    for row in rows:
        if row["label"] != "Y":
            continue
        body = (row["native"].get("run") or {}).get("response", {}).get("answer", "")
        key = row["question_id"], hashlib.sha256(body.encode()).hexdigest()
        human, llm = ratings["human"][key], ratings["llm"][key]
        if human["facts_sha256"] != llm["facts_sha256"]:
            raise ValueError("Annotators used different required facts")
        single = len(facts[row["question_id"]]["required_facts"]) == 1
        if single and not facts[row["question_id"]]["fact_count_exception"]["human_authorized"]:
            raise ValueError("Unsigned single-fact exception")
        result = {
            k: row[k] for k in ["repeat", "group_sha256", "question_id", "primary", "control"]
        }
        result["single_fact_exception"] = single
        for name, item in [("human", human), ("llm", llm)]:
            points = sum(f["score"] for f in item["facts"])
            result[name + "_coverage"] = points / (2 * len(item["facts"]))
            result[name + "_complete"] = int(all(f["score"] == 2 for f in item["facts"]))
            result[name + "_earned_points"] = points
            result[name + "_possible_points"] = 2 * len(item["facts"])
        scored.append(result)
        for a, b in zip(human["facts"], llm["facts"], strict=True):
            pairs.append(
                {
                    "repeat": row["repeat"],
                    "group_sha256": row["group_sha256"],
                    "agreement": int(a["score"] == b["score"]),
                    "primary": row["primary"],
                    "single_fact_exception": single,
                }
            )
            if a["score"] != b["score"]:
                disagreements[(key, a["fact_id"])] = {
                    "question_id": key[0],
                    "answer_sha256": key[1],
                    "fact_id": a["fact_id"],
                    "human": a,
                    "llm": b,
                    "status": "unresolved",
                    "single_fact_exception": single,
                }

    def group_metrics(exception: bool) -> dict[str, Any]:
        selected = [r for r in scored if r["primary"] and r["single_fact_exception"] == exception]
        metrics = {}
        for name in ["human", "llm"]:
            metrics[name + "_fact_coverage"] = metric(selected, name + "_coverage")
            metrics[name + "_all_facts_complete"] = metric(
                selected, name + "_complete", binary=True
            )
            metrics[name + "_fact_coverage"].update(
                {
                    "earned_points": sum(r[name + "_earned_points"] for r in selected),
                    "possible_points": sum(r[name + "_possible_points"] for r in selected),
                    "aggregation": "macro per-question ordinal coverage; "
                    "raw score points reported separately",
                }
            )
        metrics["exact_ordinal_agreement"] = metric(
            [r for r in pairs if r["primary"] and r["single_fact_exception"] == exception],
            "agreement",
        )
        return metrics

    primary = [r for r in scored if r["primary"]]
    counts = {}
    for repeat in sorted({r["repeat"] for r in primary}):
        current = [r for r in primary if r["repeat"] == repeat]
        exceptions = sum(r["single_fact_exception"] for r in current)
        counts[str(repeat)] = {
            "all_Y": len(current),
            "main_eligible_Y": len(current) - exceptions,
            "single_fact_Y": exceptions,
        }
    return {
        "metrics": group_metrics(False),
        "single_fact_exception_metrics": group_metrics(True),
        "denominator_accounting_per_repeat": counts,
        "single_fact_question_scores": [r for r in scored if r["single_fact_exception"]],
        "annotators": {n: p["annotator"] for n, p in payloads.items()},
        "disagreements": list(disagreements.values()),
        "consensus_score": None,
        "complete": True,
        "control_fact_scores": [r for r in scored if r["control"]],
        "single_fact_controls_preserved": True,
    }


def annotation_summary(stage: str, partition: str) -> None:
    load_policy()
    output, rows, template = review.rating_paths(stage, partition)
    definitions = approved_definitions(partition)
    if definitions is None or definitions.get("annotation_policy_sha256") != digest(POLICY):
        raise ValueError("Definitions need frozen A1 provenance")
    payloads = {}
    for name in ["human", "llm"]:
        path = output / f"{name}_ratings.json"
        verify(path)
        payload = read(path)
        validate_human_ratings({**payload, "is_human": True}, template)
        if bool(payload["is_human"]) != (name == "human"):
            raise ValueError("Human/LLM provenance mismatch")
        payloads[name] = payload
    if payloads["human"]["annotator"] == payloads["llm"]["annotator"]:
        raise ValueError("Independent different annotators required")
    value = summarize_scores(rows, payloads, definitions)
    value.update(
        {
            "annotation_policy": "A1",
            "annotation_policy_sha256": digest(POLICY),
            "native_summary_sha256": digest(output / "summary.json"),
            "native_rerun": False,
        }
    )
    write_new(output / "annotation_summary.a1.json", value)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--freeze-facts", type=Path)
    actions.add_argument("--judge", action="store_true")
    actions.add_argument("--import-human", type=Path)
    actions.add_argument("--summarize", action="store_true")
    parser.add_argument("--stage", default="baseline-v0-quick")
    parser.add_argument("--partition", choices=["tune", "held-out"], default="tune")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", args.stage):
        raise ValueError("Unsafe stage name")
    load_policy()
    if args.freeze_facts:
        freeze_facts(args.freeze_facts)
    elif args.judge:
        definitions = approved_definitions(args.partition)
        if definitions is None or definitions.get("annotation_policy_sha256") != digest(POLICY):
            raise ValueError("Freeze human-approved A1 definitions first")
        review.judge(args.stage, args.partition)
    elif args.import_human:
        definitions = approved_definitions(args.partition)
        if definitions is None or definitions.get("annotation_policy_sha256") != digest(POLICY):
            raise ValueError("Freeze human-approved A1 definitions first")
        review.import_human(args.stage, args.partition, args.import_human)
    elif args.summarize:
        annotation_summary(args.stage, args.partition)
        paths = [
            STATE / "runs" / args.stage / part / "annotation_summary.a1.json"
            for part in ["tune", "held-out"]
        ]
        if args.stage == "baseline-v0-quick" and all(p.exists() for p in paths):
            for path in paths:
                verify(path)
                if not read(path).get("complete"):
                    raise ValueError("Incomplete annotation summary")
            write_new(
                STATE / "baseline_v0.annotation_acceptance.json",
                {
                    "status": "complete",
                    "baseline_stage": args.stage,
                    "annotation_policy": "A1",
                    "annotation_policy_sha256": digest(POLICY),
                    "summary_sha256": {str(p.relative_to(ROOT)): digest(p) for p in paths},
                    "heldout_reexecuted": False,
                    "disagreements_retained": True,
                },
            )
    return 0
