"""Immutable inputs, grouped stratification and an append-only held-out ledger."""

from __future__ import annotations

import hashlib
import json
import os
import random
import subprocess
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "evals/protocol_v0"
SPLITS = ROOT / "splits.json"
SEED = 20261004
OFFICIAL_FILES = (
    "training_and_dev/training_Q_A.json",
    "training_and_dev/dev_Q_A.json",
    "validation/validation_reference.json",
)
ENVIRONMENT = {
    "AGENT_RETRIEVAL_BACKEND": "techqa",
    "AGENT_PROFILE": "ollama",
    "AGENT_EMBEDDING_PROVIDER": "auto",
    "AGENT_MODEL": "qwen2.5:7b",
    "AGENT_EMBEDDING_MODEL": "nomic-embed-text",
    "AGENT_TOP_K": "8",
    "AGENT_MAX_CONTEXT_TOKENS": "2400",
    "AGENT_MAX_SOURCES": "8",
    "AGENT_MIN_RELEVANCE": "0.20",
    "AGENT_TOOL_TIMEOUT": "30",
    "AGENT_LLM_TIMEOUT": "120",
    "AGENT_OLLAMA_URL": "http://localhost:11434",
    "TECHQA_PROFILE": "full",
    "TECHQA_DENSE_BACKEND": "semantic",
    "TECHQA_RERANKER": "nomic",
    "TECHQA_RERANK_WEIGHTS": "0.50,0.30,0.20",
    "TECHQA_GENERATION": "extractive",
    "TECHQA_FACT_AUDIT": "0",
    "TECHQA_AGENT_CANDIDATE_K": "20",
    "TECHQA_SEMANTIC_URL": "http://127.0.0.1:11435",
    "TECHQA_RERANKER_TIMEOUT": "120",
    "RETRIEVAL_CANDIDATE_K": "30",
    "RETRIEVAL_RERANK_K": "20",
    "RRF_RANK_CONSTANT": "60",
    "MAX_CONTEXT_TOKENS": "8000",
    "MAX_CHUNKS_PER_DOCUMENT": "2",
    "TECHQA_FALLBACK_THRESHOLD": "0.5",
}


def now() -> str:
    return datetime.now(UTC).isoformat()


def canonical(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf8")


def digest(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(8 * 1024 * 1024):
            sha.update(block)
    return sha.hexdigest()


def read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf8"))


def write_new(path: Path, value: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(canonical(value))
    sha = digest(path)
    with path.with_suffix(path.suffix + ".sha256").open(
        "x", encoding="utf8", newline="\n"
    ) as stream:
        stream.write(f"{sha}  {path.name}\n")
    return sha


def verify(path: Path) -> None:
    if digest(path) != path.with_suffix(path.suffix + ".sha256").read_text().split()[0]:
        raise ValueError(f"Frozen file changed: {path}")


def sut_files() -> list[Path]:
    paths = []
    excluded = {
        "evals.py",
        "retrieval_eval.py",
        "evaluate.py",
        "calibrate.py",
        "protocol.py",
        "metrics.py",
    }
    for directory in [
        ROOT / "src/rag",
        *[
            ROOT / "enterprise-ai-agent" / part
            for part in ("agents", "models", "tools", "vectorstore", "api")
        ],
    ]:
        paths.extend(p for p in directory.rglob("*.py") if p.name not in excluded)
    paths.extend(p for p in (ROOT / "config").rglob("*") if p.suffix in {".json", ".yaml"})
    return sorted(set(paths))


def sut_manifest() -> dict[str, Any]:
    files = {p.relative_to(ROOT).as_posix(): digest(p) for p in sut_files()}
    return {"files": files, "sha256": hashlib.sha256(canonical(files)).hexdigest()}


def evaluator_manifest() -> dict[str, str]:
    paths = [
        ROOT / "run_eval.py",
        ROOT / "review_eval.py",
        *sorted((ROOT / "evaluation_protocol").glob("*.py")),
    ]
    return {p.relative_to(ROOT).as_posix(): digest(p) for p in paths}


def query(row: dict[str, Any]) -> str:
    title, text = str(row["QUESTION_TITLE"]).strip(), str(row["QUESTION_TEXT"]).strip()
    return title if not text or text == title else f"{title}\n{text}"


def initialize() -> dict[str, Any]:
    if SPLITS.exists() or STATE.exists():
        raise FileExistsError("Protocol exists: refusing to repartition or replace frozen inputs")
    data_root = Path(
        os.getenv(
            "TECHQA_DATA_ROOT", str(ROOT / "enterprise-ai-agent/data/techqa/extracted/TechQA")
        )
    )
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    sources = []
    for rel in OFFICIAL_FILES:
        path = data_root / rel
        rows = read(path)
        sources.append({"relative_path": rel, "sha256": digest(path), "records": len(rows)})
        for index, row in enumerate(rows):
            if row["ANSWERABLE"] not in {"Y", "N"}:
                raise ValueError("Unsupported official label")
            # Exact original title/body; no normalization, relabeling or rewriting of gold.
            key = hashlib.sha256(
                canonical([row["QUESTION_TITLE"], row["QUESTION_TEXT"]])
            ).hexdigest()
            groups[key].append(
                {"official_file": rel, "official_row": index, "group_sha256": key, "record": row}
            )
    strata: dict[str, list[str]] = defaultdict(list)
    for key, records in sorted(groups.items()):
        signature = "+".join(sorted({r["record"]["ANSWERABLE"] for r in records}))
        strata[signature].append(key)
    rng = random.Random(SEED)
    partition_keys: dict[str, list[str]] = {"tune": [], "held-out": []}
    for keys in strata.values():
        rng.shuffle(keys)
        boundary = round(len(keys) * 0.6)
        partition_keys["tune"].extend(keys[:boundary])
        partition_keys["held-out"].extend(keys[boundary:])
    partitions = {
        name: [r for key in sorted(keys) for r in groups[key]]
        for name, keys in partition_keys.items()
    }
    # Historical saved responses were retrieved before any gold was used in scoring.
    history_path = ROOT / "enterprise-ai-agent/evaluation/results/techqa_semantic_v3/runs.json"
    history = {r["question_id"]: r for r in read(history_path)}
    success = [
        r
        for r in partitions["tune"]
        if r["record"]["ANSWERABLE"] == "Y"
        and r["record"]["ANSWER"]
        and len({x["record"]["ANSWERABLE"] for x in groups[r["group_sha256"]]}) == 1
        and (history.get(r["record"]["QUESTION_ID"], {}).get("answer_quality") or 0) >= 0.6
    ]
    success.sort(
        key=lambda r: hashlib.sha256(
            f"{SEED}:controls:{r['record']['QUESTION_ID']}".encode()
        ).hexdigest()
    )
    controls, seen = [], set()
    for row in success:
        if row["group_sha256"] not in seen:
            controls.append(row)
            seen.add(row["group_sha256"])
        if len(controls) == 10:
            break
    if len(controls) < 10:
        raise ValueError("Insufficient historical controls; do not silently weaken criteria")
    quick: dict[str, list[str]] = {}
    for name, records in partitions.items():
        chosen: list[dict[str, Any]] = []
        seen = {r["group_sha256"] for r in chosen}
        for label, count in [("Y", 20), ("N", 10)]:
            eligible = [
                r
                for r in records
                if r["record"]["ANSWERABLE"] == label
                and (label == "N" or r["record"]["ANSWER"])
                and len({x["record"]["ANSWERABLE"] for x in groups[r["group_sha256"]]}) == 1
            ]
            eligible.sort(
                key=lambda r: hashlib.sha256(
                    f"{SEED}:quick:{r['group_sha256']}".encode()
                ).hexdigest()
            )
            for row in eligible:
                if sum(r["record"]["ANSWERABLE"] == label for r in chosen) >= count:
                    break
                if row["group_sha256"] not in seen:
                    chosen.append(row)
                    seen.add(row["group_sha256"])
            if sum(r["record"]["ANSWERABLE"] == label for r in chosen) != count:
                raise ValueError("Insufficient independent quick-set questions")
        quick[name] = [r["record"]["QUESTION_ID"] for r in chosen]
    STATE.mkdir(parents=True)
    # Immediately hash and freeze held-out BEFORE tune artifacts or any new evaluation.
    hashes = {"held-out": write_new(STATE / "held-out.json", partitions["held-out"])}
    hashes["tune"] = write_new(STATE / "tune.json", partitions["tune"])
    control_sha = write_new(
        STATE / "controls.json",
        {
            "selection": "tune-only, 10 unique query groups; historical body-F1 >= .6 "
            "and correct citation",
            "status": "historically successful; factual completeness awaits human annotation",
            "historical_path": history_path.relative_to(ROOT).as_posix(),
            "historical_sha256": digest(history_path),
            "records": [
                {
                    "question_id": r["record"]["QUESTION_ID"],
                    "group_sha256": r["group_sha256"],
                    "original_run": history[r["record"]["QUESTION_ID"]],
                }
                for r in controls
            ],
        },
    )
    manifest: dict[str, Any] = {
        "version": 1,
        "seed": SEED,
        "created_utc": now(),
        "requested_tune_fraction": 0.6,
        "stratification": "exact title/body groups, stratified by Y / N / mixed label signature",
        "official_sources": sources,
        "official_records": sum(len(r) for r in partitions.values()),
        "unique_query_groups": len(groups),
        "historical_exposure": {
            "status": "retrospective holdout, NOT prospectively unseen",
            "training": "all 600 previously used for calibration",
            "development": "all 310 previously used in retrieval and Enterprise evaluations",
            "validation": "20 previously evaluated; exact text overlaps grouped with other splits",
        },
        "partitions": {
            name: {
                "file": f"evals/protocol_v0/{name}.json",
                "sha256": hashes[name],
                "records": len(rows),
                "counts": {
                    label: sum(r["record"]["ANSWERABLE"] == label for r in rows)
                    for label in ["Y", "N"]
                },
                "query_groups": len(partition_keys[name]),
                "quick_question_ids": quick[name],
                "question_ids": [r["record"]["QUESTION_ID"] for r in rows],
            }
            for name, rows in partitions.items()
        },
        "controls_sha256": control_sha,
        "mixed_label_groups": len(strata.get("N+Y", [])),
        "empty_official_answer_Y": sum(
            not r["record"]["ANSWER"] and r["record"]["ANSWERABLE"] == "Y"
            for rows in partitions.values()
            for r in rows
        ),
        "heldout_budget": "one stage-end invocation with 3 repeats; both counters logged",
    }
    write_new(SPLITS, manifest)
    (STATE / "eval_protocol.v0.md").write_bytes((ROOT / "eval_protocol.md").read_bytes())
    write_new(
        STATE / "protocol_document.json",
        {"file": "eval_protocol.v0.md", "sha256": digest(STATE / "eval_protocol.v0.md")},
    )
    write_new(
        STATE / "baseline_v0.config.json",
        {
            "name": "baseline-v0",
            "created_utc": now(),
            "environment": {k: os.getenv(k, v) for k, v in ENVIRONMENT.items()},
            "sut": sut_manifest(),
            "split_sha256": digest(SPLITS),
            "repeats": 3,
            "git_commit": subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
            ).stdout.strip(),
            "scope": "current default Enterprise RAG Agent, shared full-corpus TechQA retriever",
            "other_agent_services": "not evaluated by this baseline",
        },
    )
    return manifest


def load_config(name: str) -> dict[str, Any]:
    verify(SPLITS)
    baseline_path = STATE / "baseline_v0.config.json"
    verify(baseline_path)
    baseline = read(baseline_path)
    if name == "baseline-v0":
        config = baseline
    else:
        freeze = STATE / "baseline_v0.quick.freeze.json"
        verify(freeze)
        acceptance = STATE / "baseline_v0.annotation_acceptance.json"
        verify(acceptance)
        if read(acceptance)["status"] != "complete":
            raise ValueError("Baseline fact annotation is incomplete; ablations remain locked")
        path = STATE / "configurations" / f"{name}.json"
        verify(path)
        config = read(path)
        changes = [
            k
            for k in baseline["environment"]
            if baseline["environment"][k] != config["environment"].get(k)
        ]
        if set(config["environment"]) != set(baseline["environment"]) or len(changes) != 1:
            raise ValueError("Ablation must change exactly ONE environment setting from v0")
        if config["sut"] != baseline["sut"] or config["split_sha256"] != baseline["split_sha256"]:
            raise ValueError(
                "Source/split change requires a separately preregistered code protocol"
            )
    if config["sut"] != sut_manifest():
        raise ValueError(
            "SUT differs from frozen source; no retrieval/generation/critic edits permitted"
        )
    return config


def ledger(event: str, stage: str, **fields: Any) -> dict[str, Any]:
    path = STATE / "heldout_ledger.jsonl"
    history = []
    if path.exists():
        history = [json.loads(line) for line in path.read_text(encoding="utf8").splitlines()]
    previous = "0" * 64
    for record in history:
        claimed = record["entry_sha256"]
        payload = {k: v for k, v in record.items() if k != "entry_sha256"}
        if (
            record["previous_sha256"] != previous
            or hashlib.sha256(canonical(payload)).hexdigest() != claimed
        ):
            raise ValueError("Held-out ledger hash chain changed")
        previous = claimed
    if event == "stage_started" and any(
        r["event"] == event and r["stage"] == stage for r in history
    ):
        raise ValueError("Held-out stage already consumed, including failed attempts")
    record = {
        "time_utc": now(),
        "event": event,
        "stage": stage,
        "previous_sha256": previous,
        "cumulative_stage_invocations": sum(r["event"] == "stage_started" for r in history)
        + int(event == "stage_started"),
        "cumulative_repeat_starts": sum(r["event"] == "repeat_started" for r in history)
        + int(event == "repeat_started"),
        **fields,
    }
    record["entry_sha256"] = hashlib.sha256(canonical(record)).hexdigest()
    with path.open("a", encoding="utf8", newline="\n") as stream:
        stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    return record
