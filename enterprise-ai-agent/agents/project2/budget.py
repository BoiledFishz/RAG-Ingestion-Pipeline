"""Request-wide atomic reservations; failures and retries consume attempts."""

from __future__ import annotations

import time
import hashlib
import json
from collections import Counter
from pathlib import Path
from threading import RLock
from typing import Any


class BudgetExceeded(TimeoutError):
    pass


def read_frozen_limits(root: Path | None = None) -> dict[str, Any]:
    root = root or Path(__file__).resolve().parents[3]
    from agents.project2.calibration_profile import read_v031
    selected = read_v031(root)
    if selected is not None:
        return selected
    folder = root / "evals/project2-v1/calibration_v03"
    profile = folder / "budget_frozen.json"
    if not profile.is_file():
        return {"attempts": 16, "llm_calls": 6, "seconds": 90}
    data = json.loads(profile.read_text(encoding="utf-8"))
    if data.get("status") != "frozen" or data.get("version") != "project2-v0.3-budget-v1":
        raise ValueError("Unverified Project 2 budget profile")
    manifest_path = folder / "frozen_manifest.json"
    if hashlib.sha256(manifest_path.read_bytes()).hexdigest() != data["calibration_manifest_sha256"]:
        raise ValueError("Budget calibration manifest changed")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if set(manifest["files"]) != {"protocol.json", "requests.jsonl", "summary.json"}:
        raise ValueError("Incomplete calibration evidence")
    for name, digest in manifest["files"].items():
        if hashlib.sha256((folder/name).read_bytes()).hexdigest() != digest:
            raise ValueError(f"Budget calibration evidence changed: {name}")
    result = json.loads((folder/"summary.json").read_text(encoding="utf-8"))
    if result["status"] != "selected" or result["requests"] != result["expected"] or result["expected"] != 300:
        raise ValueError("Budget calibration incomplete/censored/fused")
    if result["limits"] != data["limits"]:
        raise ValueError("Budget differs from observed P95 selection")
    docs = root/"specs/project2/v0.3"
    if hashlib.sha256((docs/"version_manifest.json").read_bytes()).hexdigest() != data["spec_manifest_sha256"]:
        raise ValueError("Budget authorized specification changed")
    limits = data["limits"]
    if not (isinstance(limits["attempts"], int) and 1 <= limits["attempts"] <= 40
            and isinstance(limits["llm_calls"], int) and 1 <= limits["llm_calls"] <= 15 and limits["seconds"] > 0):
        raise ValueError("Budget exceeds authorized P95 envelope")
    return limits


def prepare_budget_configuration() -> dict[str, Any]:
    from agents.project2.budget_cache import verified_limits
    return verified_limits(Path(__file__).resolve().parents[3], read_frozen_limits)


class Budget:
    def __init__(self, *, seconds: float | None = None, attempts: int | None = None, llm_calls: int | None = None) -> None:
        started_monotonic, started_absolute = time.monotonic(), time.time()
        approved = prepare_budget_configuration()
        seconds = approved["seconds"] if seconds is None else seconds
        attempts = approved["attempts"] if attempts is None else attempts
        llm_calls = approved["llm_calls"] if llm_calls is None else llm_calls
        if not 0 < seconds <= approved["seconds"] or not 1 <= attempts <= approved["attempts"] or not 1 <= llm_calls <= approved["llm_calls"]:
            raise ValueError("Cannot enlarge approved hard call limits")
        self.deadline = started_monotonic + seconds
        self.absolute_deadline = started_absolute + seconds
        self.max_attempts, self.max_llm_calls = attempts, llm_calls
        self.attempts, self.llm_calls = 0, 0
        self.kinds: Counter[str] = Counter()
        self.lock = RLock()
        self.cancelled = False
        self.run_id: str | None = None
        self.database_result: Any = None

    def remaining(self, local_limit: float | None = None) -> float:
        with self.lock:
            value = self.deadline - time.monotonic()
            if self.cancelled or value <= 0:
                raise BudgetExceeded("request_deadline_exhausted")
            return value if local_limit is None else min(value, local_limit)

    def reserve(self, kind: str) -> None:
        with self.lock:
            self.remaining()
            if self.attempts >= self.max_attempts:
                raise BudgetExceeded("dependency_attempt_limit")
            if kind == "llm" and self.llm_calls >= self.max_llm_calls:
                raise BudgetExceeded("llm_attempt_limit")
            self.attempts += 1
            self.llm_calls += int(kind == "llm")
            self.kinds[kind] += 1

    def cancel(self) -> None:
        with self.lock:
            self.cancelled = True

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            return {"attempts": self.attempts, "llm_calls": self.llm_calls, "attempts_by_kind": dict(self.kinds),
                    "absolute_deadline": self.absolute_deadline, "observed_tokens": None,
                    "estimated_tokens": None, "cost": None}
