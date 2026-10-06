"""Preregistered repeated native evaluation, with gold restricted to scoring."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import random
import re
import subprocess
import sys
import urllib.request
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any

from evaluation_protocol.annotations import (
    approved_definitions,
    fact_drafts,
    human_rating_template,
)
from evaluation_protocol.statistics import metric
from evaluation_protocol.storage import (
    ROOT,
    SEED,
    SPLITS,
    STATE,
    canonical,
    digest,
    evaluator_manifest,
    initialize,
    ledger,
    load_config,
    now,
    query,
    read,
    sut_manifest,
    verify,
    write_new,
)

LOGGER = logging.getLogger(__name__)
BINARY = {
    "recall_at_5",
    "recall_at_10",
    "correct_document_cited",
    "y_answered",
    "n_refusal_proxy",
    "error_rate",
    "reranker_fallback_rate",
}


def document_id(chunk: str) -> str:
    parts = chunk.split(":", 3)
    return parts[1] if len(parts) >= 3 and parts[0] == "techqa" else chunk


def body_f1(actual: str, expected: str) -> float:
    actual = re.sub(r"\[(?:S?\d+|evidence)\]", "", actual).casefold()
    a = Counter(re.findall(r"\w+", actual))
    b = Counter(re.findall(r"\w+", expected.casefold()))
    common = sum((a & b).values())
    return 2 * common / (sum(a.values()) + sum(b.values())) if a and b else 0.0


def score(
    wrapped: dict[str, Any], native: dict[str, Any], repeat: int, *, primary: bool, control: bool
) -> dict[str, Any]:
    # This function is invoked ONLY AFTER the inference worker has returned.
    row = wrapped["record"]
    run = native["run"] or {}
    response, trace = run.get("response", {}), run.get("trace", {})
    ids = native.get("pipeline", {}).get("candidate_ids", [])
    target = row["DOCUMENT"] if row["ANSWERABLE"] == "Y" else None
    y = target is not None
    cited = any(document_id(s["chunk_id"]) == target for s in response.get("sources", []))
    f1 = body_f1(response.get("answer", ""), row["ANSWER"]) if y and row["ANSWER"] else None
    return {
        "question_id": row["QUESTION_ID"],
        "group_sha256": wrapped["group_sha256"],
        "repeat": repeat,
        "label": row["ANSWERABLE"],
        "primary": primary,
        "control": control,
        "native": native,
        "recall_at_5": int(target in [document_id(c) for c in ids[:5]]) if y else None,
        "recall_at_10": int(target in [document_id(c) for c in ids[:10]]) if y else None,
        "mrr": next((1 / i for i, c in enumerate(ids, 1) if document_id(c) == target), 0)
        if y
        else None,
        "context_precision_at_5": sum(document_id(c) == target for c in ids[:5]) / 5 if y else None,
        "body_token_f1": f1,
        "body_f1_correct_citation": f1 * int(cited) if f1 is not None else None,
        "correct_document_cited": int(cited) if y else None,
        "y_answered": int(bool(response.get("sources"))) if y else None,
        "n_refusal_proxy": int(trace.get("status") == "unanswerable") if not y else None,
        "error_rate": int(bool(native["error"])),
        "latency_ms": native["wall_latency_ms"],
        "reranker_fallback_rate": int(native.get("pipeline", {}).get("reranker_fallback", False)),
        "llm_calls": native["cost"]["llm_calls"],
        "llm_tokens": native["cost"]["prompt_eval_count"] + native["cost"]["eval_count"],
    }


def get_json(url: str) -> Any:
    with urllib.request.urlopen(url, timeout=120) as response:
        return json.load(response)


def preflight(config: dict[str, Any]) -> dict[str, Any]:
    environment = config["environment"]
    health = get_json(environment["TECHQA_SEMANTIC_URL"] + "/healthz")
    if health.get("scope") != "full" or not health.get("complete"):
        raise ValueError("A complete full-corpus semantic index is required")
    tags = get_json(environment["AGENT_OLLAMA_URL"] + "/api/tags")
    models = {m["name"]: m["digest"] for m in tags["models"]}
    selected = {}
    for name in [environment["AGENT_MODEL"], environment["AGENT_EMBEDDING_MODEL"]]:
        key = name if name in models else name + ":latest"
        if key not in models:
            raise ValueError(f"Required model not installed: {name}")
        selected[key] = models[key]
    state = {
        "models": selected,
        "semantic_health": health,
        "python": sys.version,
        "python_executable": sys.executable,
        "evaluator": evaluator_manifest(),
        "dependencies": subprocess.run(
            [sys.executable, "-m", "pip", "freeze"], capture_output=True, text=True, check=True
        ).stdout.splitlines(),
    }
    path = STATE / "baseline_v0.runtime.json"
    if path.exists():
        verify(path)
        if read(path) != state:
            raise ValueError("Model/index/runtime differs from frozen baseline")
    else:
        write_new(path, state)
        with zipfile.ZipFile(
            STATE / "baseline_v0.source.zip", "x", zipfile.ZIP_DEFLATED
        ) as archive:
            for name in config["sut"]["files"]:
                archive.write(ROOT / name, name)
        write_new(
            STATE / "baseline_v0.source_snapshot.json",
            {"sha256": digest(STATE / "baseline_v0.source.zip"), "sut": config["sut"]},
        )
    artifacts = STATE / "baseline_v0.index_artifacts.json"
    if not artifacts.exists():
        identities = {}
        for rel in [
            ".rag_data/techqa_semantic/index.faiss",
            ".rag_data/techqa_semantic/chunks.sqlite",
            ".rag_data/techqa_full.sqlite",
        ]:
            path = ROOT / rel
            info = path.stat()
            LOGGER.info("Freezing actual index bytes: %s (%d bytes)", rel, info.st_size)
            identities[rel] = {
                "sha256": digest(path),
                "size": info.st_size,
                "mtime_ns": info.st_mtime_ns,
            }
        write_new(artifacts, identities)
    check_artifacts()
    return state


def check_artifacts() -> None:
    path = STATE / "baseline_v0.index_artifacts.json"
    verify(path)
    for rel, identity in read(path).items():
        info = (ROOT / rel).stat()
        if (info.st_size, info.st_mtime_ns) != (identity["size"], identity["mtime_ns"]):
            raise ValueError("Frozen index artifact changed: " + rel)


def summarize(
    rows: list[dict[str, Any]], config: dict[str, Any], partition: str, scope: str, stage: str
) -> dict[str, Any]:
    primary = [row for row in rows if row["primary"]]
    keys = [
        "recall_at_5",
        "recall_at_10",
        "mrr",
        "context_precision_at_5",
        "body_token_f1",
        "body_f1_correct_citation",
        "correct_document_cited",
        "y_answered",
        "n_refusal_proxy",
        "error_rate",
        "latency_ms",
        "llm_calls",
        "llm_tokens",
        "reranker_fallback_rate",
    ]
    controls = [row for row in rows if row["control"]]
    original = {
        r["question_id"]: r["original_run"] for r in read(STATE / "controls.json")["records"]
    }
    regressions = []
    for row in controls:
        before = original[row["question_id"]]
        if (
            not row["y_answered"]
            or not row["correct_document_cited"]
            or (row["body_f1_correct_citation"] < (before["answer_quality"] or 0))
        ):
            regressions.append(
                {
                    "question_id": row["question_id"],
                    "repeat": row["repeat"],
                    "historical_f1": before["answer_quality"],
                    "current_f1": row["body_f1_correct_citation"],
                }
            )
    return {
        "config": config["name"],
        "stage": stage,
        "partition": partition,
        "scope": scope,
        "created_utc": now(),
        "baseline": "v0",
        "repeats": 3,
        "official_question_count": len(primary) // 3,
        "counts_per_repeat": {
            label: sum(r["label"] == label for r in primary) // 3 for label in ["Y", "N"]
        },
        "split_sha256": digest(SPLITS),
        "sut_sha256": config["sut"]["sha256"],
        "metrics": {key: metric(primary, key, binary=key in BINARY) for key in keys},
        "recall_rank_scope": "actual shared pipeline final ordered CHUNKS; "
        "pipeline returns at most 20; Agent top_k remains 8",
        "context_precision_scope": "relevant slots in pipeline top-5 / 5; missing slots are zero; "
        "not a semantic LLM context precision estimate",
        "official_f1": "token body F1 only; separate correct-citation gate, NOT fact coverage",
        "n_label_warning": "N is official DOC_IDS annotation; full-corpus refusal is a proxy, "
        "not an independently verified hallucination rate",
        "heldout_warning": read(SPLITS)["historical_exposure"],
        "fact_coverage": {
            "mean": None,
            "numerator": 0,
            "denominator": 0,
            "ci95": None,
            "interpretation": "仅描述，不作结论",
            "status": "pending human definitions "
            "and two independent ratings; no invented human scores",
        },
        "annotation_agreement": {
            "numerator": 0,
            "denominator": 0,
            "ci95": None,
            "interpretation": "仅描述，不作结论",
            "status": "pending",
        },
        "controls": {
            "questions": len({r["question_id"] for r in controls}),
            "historical_regressions": regressions,
            "historical_no_regression": not regressions if controls else None,
            "fact_complete_success": "not verified until human annotation",
        },
        "acceptance": "native results frozen; factual annotation acceptance PENDING",
        "full_replication": scope == "full",
    }


def compare_to_v0(rows: list[dict[str, Any]], partition: str) -> dict[str, Any]:
    path = STATE / "runs/baseline-v0-quick" / partition / "runs.json"
    verify(path)
    reference = {(r["question_id"], r["repeat"]): r for r in read(path)}
    if set(reference) != {(r["question_id"], r["repeat"]) for r in rows}:
        raise ValueError("Ablation requires the identical baseline question/repetition set")
    failures = []
    deltas = []
    keys = [
        "recall_at_5",
        "recall_at_10",
        "mrr",
        "context_precision_at_5",
        "body_f1_correct_citation",
        "correct_document_cited",
        "y_answered",
        "n_refusal_proxy",
        "error_rate",
        "latency_ms",
        "llm_calls",
        "llm_tokens",
    ]
    for row in rows:
        old = reference[row["question_id"], row["repeat"]]
        if row["primary"]:
            deltas.append(
                {
                    "repeat": row["repeat"],
                    "group_sha256": row["group_sha256"],
                    **{key: row[key] - old[key] if row[key] is not None else None for key in keys},
                }
            )
        if row["control"]:
            worsened = [
                key
                for key in ["y_answered", "correct_document_cited", "body_f1_correct_citation"]
                if row[key] < old[key]
            ]
            if worsened:
                failures.append(
                    {
                        "question_id": row["question_id"],
                        "repeat": row["repeat"],
                        "worsened": worsened,
                    }
                )
    return {
        "baseline": "v0",
        "paired_delta_ci": {k: metric(deltas, k) for k in keys},
        "control_regressions": failures,
        "native_control_gate": not failures,
        "fact_control_gate": "pending dual independent ratings of candidate answers",
        "production_approval": False,
    }


def run_partition(config: dict[str, Any], partition: str, scope: str, stage: str) -> Path:
    manifest = read(SPLITS)
    input_path = ROOT / manifest["partitions"][partition]["file"]
    verify(input_path)
    inputs = read(input_path)
    controls = {r["question_id"] for r in read(STATE / "controls.json")["records"]}
    primary_ids = set(
        manifest["partitions"][partition]["quick_question_ids"]
        if scope == "quick"
        else manifest["partitions"][partition]["question_ids"]
    )
    selected = [
        r
        for r in inputs
        if r["record"]["QUESTION_ID"] in primary_ids
        or (partition == "tune" and r["record"]["QUESTION_ID"] in controls)
    ]
    output = STATE / "runs" / stage / partition
    output.mkdir(parents=True, exist_ok=False)
    if partition == "held-out":
        tune = STATE / "runs" / stage / "tune" / "summary.json"
        verify(tune)
        prior = read(tune)
        if prior["repeats"] != 3:
            raise ValueError("Held-out requires a completed three-repeat tune stage")
        if (prior["config"], prior["scope"], prior["sut_sha256"]) != (
            config["name"],
            scope,
            config["sut"]["sha256"],
        ):
            raise ValueError("Held-out cannot follow a tune run with different configuration")
        ledger(
            "stage_started",
            stage,
            config=config["name"],
            scope=scope,
            heldout_sha256=digest(input_path),
            planned_repeats=3,
            planned_questions_per_repeat=len(selected),
        )
    draft_path = STATE / f"facts_{partition}.draft.json"
    definitions = read(draft_path) if draft_path.exists() else fact_drafts(inputs, partition)
    worker_log = (output / "worker.log").open("x", encoding="utf8")
    worker = subprocess.Popen(
        [sys.executable, "-m", "evaluation_protocol.worker", json.dumps(config["environment"])],
        cwd=ROOT,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=worker_log,
        text=True,
        encoding="utf8",
        env={**os.environ, "PYTHONUTF8": "1"},
    )
    rows = []
    try:
        with (output / "native.jsonl").open("x", encoding="utf8", newline="\n") as stream:
            for repeat in range(1, 4):
                if partition == "held-out":
                    ledger("repeat_started", stage, repeat=repeat)
                order = list(selected)
                random.Random(SEED + repeat).shuffle(order)
                for index, wrapped in enumerate(order, 1):
                    # No gold, QA identity, or target IDs cross the inference-process boundary.
                    worker.stdin.write(json.dumps({"query": query(wrapped["record"])}) + "\n")
                    worker.stdin.flush()
                    line = worker.stdout.readline()
                    if not line:
                        raise RuntimeError(
                            "Inference worker exited; see worker.log. No silent retry."
                        )
                    native = json.loads(line)
                    scored = score(
                        wrapped,
                        native,
                        repeat,
                        primary=wrapped["record"]["QUESTION_ID"] in primary_ids,
                        control=wrapped["record"]["QUESTION_ID"] in controls,
                    )
                    stream.write(json.dumps(scored, ensure_ascii=False) + "\n")
                    stream.flush()
                    rows.append(scored)
                    LOGGER.info(
                        "%s repetition %d/3 completed %d/%d", partition, repeat, index, len(order)
                    )
                if partition == "held-out":
                    ledger("repeat_completed", stage, repeat=repeat, completed_questions=len(order))
        if config["sut"] != sut_manifest():
            raise ValueError("Source changed DURING evaluation; stage invalid")
        if evaluator_manifest() != read(STATE / "baseline_v0.runtime.json")["evaluator"]:
            raise ValueError("Evaluator changed DURING evaluation; stage invalid")
        check_artifacts()
        verify(input_path)
        write_new(output / "runs.json", rows)
        summary = summarize(rows, config, partition, scope, stage)
        write_new(output / "summary.json", summary)
        if config["name"] != "baseline-v0":
            write_new(output / "comparison_to_v0.json", compare_to_v0(rows, partition))
        human_rating_template(
            rows, approved_definitions(partition) or definitions, partition, output
        )
        if partition == "held-out":
            event = ledger("stage_completed", stage, summary_sha256=digest(output / "summary.json"))
            write_new(output / "heldout_usage.json", event)
        LOGGER.info("%s complete: %s", partition, output / "summary.json")
        return output
    except BaseException as exc:
        if partition == "held-out":
            ledger(
                "stage_failed", stage, completed_observations=len(rows), error=type(exc).__name__
            )
        raise
    finally:
        if worker.stdin:
            worker.stdin.close()
        try:
            worker.wait(timeout=15)
        except subprocess.TimeoutExpired:
            worker.terminate()
            worker.wait(timeout=15)
        worker_log.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("configuration", nargs="?", default="baseline-v0")
    parser.add_argument("--init", action="store_true")
    parser.add_argument("--partition", choices=["tune", "held-out", "both"], default="tune")
    parser.add_argument("--scope", choices=["quick", "full"], default="quick")
    parser.add_argument("--stage", default="baseline-v0-quick")
    parser.add_argument("--register-change", nargs=2, metavar=("ENV_KEY", "VALUE"))
    parser.add_argument("--reason")
    args = parser.parse_args()
    if args.init:
        value = initialize()
        LOGGER.info(
            "Frozen split: %s", {name: r["counts"] for name, r in value["partitions"].items()}
        )
        return 0
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", args.stage) or not re.fullmatch(
        r"[a-zA-Z0-9_-]+", args.configuration
    ):
        raise ValueError("Unsafe stage/configuration name")
    if args.register_change:
        if args.configuration == "baseline-v0" or not args.reason:
            raise ValueError("Provide a new configuration name and single-change reason")
        baseline = load_config("baseline-v0")
        key, value = args.register_change
        if key not in baseline["environment"] or baseline["environment"][key] == value:
            raise ValueError("Exactly one known environment value must change")
        candidate = {
            **baseline,
            "name": args.configuration,
            "single_change": args.reason,
            "environment": {**baseline["environment"], key: value},
        }
        write_new(STATE / "configurations" / f"{args.configuration}.json", candidate)
        return 0
    config = load_config(args.configuration)
    if args.configuration != "baseline-v0" and args.scope != "quick":
        raise ValueError("Full ablations require a completed full v0 reference protocol")
    preflight(config)
    plan_path = STATE / "runs" / args.stage / "stage.plan.json"
    plan = {
        "stage": args.stage,
        "configuration": args.configuration,
        "scope": args.scope,
        "planned_repeats": 3,
        "config_sha256": hashlib.sha256(canonical(config)).hexdigest(),
        "split_sha256": digest(SPLITS),
        "evaluator": evaluator_manifest(),
    }
    if plan_path.exists():
        verify(plan_path)
        if read(plan_path) != plan:
            raise ValueError("Stage changed after preregistration")
    else:
        write_new(plan_path, plan)
    partitions = ["tune", "held-out"] if args.partition == "both" else [args.partition]
    for partition in partitions:
        run_partition(config, partition, args.scope, args.stage)
    paths = [STATE / "runs" / args.stage / name / "summary.json" for name in ["tune", "held-out"]]
    if args.configuration == "baseline-v0" and all(p.exists() for p in paths):
        freeze = STATE / f"baseline_v0.{args.scope}.freeze.json"
        write_new(
            freeze,
            {
                "name": "baseline v0",
                "scope": args.scope,
                "frozen_utc": now(),
                "summary_sha256": {str(p.relative_to(ROOT)): digest(p) for p in paths},
                "split_sha256": digest(SPLITS),
                "config_sha256": digest(STATE / "baseline_v0.config.json"),
                "status": "native baseline complete; human fact coverage and agreement pending",
            },
        )
    completed = [STATE / "runs" / args.stage / p / "summary.json" for p in partitions]
    return int(any(read(p)["metrics"]["error_rate"]["numerator"] for p in completed))
