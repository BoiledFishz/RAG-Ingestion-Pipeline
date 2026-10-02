"""Exercise every HTTP workflow against real local models and official TechQA data."""

from __future__ import annotations

import json
import logging
import os
import socket
import subprocess
import sys
import time
from typing import Any

import httpx

from rag.techqa.data import ROOT, question_text, questions

LOGGER = logging.getLogger(__name__)


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def main() -> int:
    rows = questions("fixture")
    known = next(r for r in rows if r["ANSWERABLE"] == "Y")
    unknown = next(r for r in rows if r["ANSWERABLE"] == "N")
    results: list[dict[str, Any]] = []
    failures = 0
    for name, cwd, application in [
        ("retrieval", ROOT, "rag.api.runtime:app"),
        ("enterprise", ROOT / "enterprise-ai-agent", "api.main:app"),
        ("agentic", ROOT / "agentic-rag-homework", "api.main:app"),
    ]:
        port = free_port()
        environment = {
            **os.environ,
            "TECHQA_PROFILE": "full",
            "TECHQA_RERANKER": "nomic",
            "MODEL_PROVIDER": "ollama",
            "AGENT_PROFILE": "ollama",
            "AGENT_RETRIEVAL_BACKEND": "techqa",
            "AGENT_QDRANT_URL": "http://localhost:6333",
            "AGENT_COLLECTION": "techqa_full_hash",
            "RAG_BACKEND": "techqa",
        }
        log_path = ROOT / f".rag_data/techqa-api-{name}.log"
        with log_path.open("w", encoding="utf-8") as log:
            process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    application,
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(port),
                ],
                cwd=cwd,
                env=environment,
                stdout=log,
                stderr=log,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            try:
                with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=180) as client:
                    deadline = time.monotonic() + 30
                    while True:
                        try:
                            client.get("/openapi.json").raise_for_status()
                            break
                        except httpx.HTTPError:
                            if time.monotonic() > deadline or process.poll() is not None:
                                raise RuntimeError(
                                    f"{name} did not start; see {log_path}"
                                ) from None
                            time.sleep(0.25)
                    query_path = "/v1/agent/query" if name == "enterprise" else "/v1/rag/query"
                    cases: list[tuple[str, str, dict[str, Any]]] = [
                        ("answerable", query_path, {"query": question_text(known)}),
                        ("official_unanswerable", query_path, {"query": question_text(unknown)}),
                    ]
                    if name == "retrieval":
                        cases += [
                            (mode, query_path, {"query": question_text(known), "mode": mode})
                            for mode in ["dense", "sparse"]
                        ]
                        cases.append(
                            (
                                "empty_filter",
                                query_path,
                                {"query": question_text(known), "filters": {"language": "zh-CN"}},
                            )
                        )
                    if name == "agentic":
                        cases += [
                            (path, "/v1/" + path, {"query": question_text(known)})
                            for path in ["planner", "research", "single-agent", "multi-agent"]
                        ]
                        cases.append(
                            (
                                "critic-loop",
                                "/v1/critic-loop",
                                {
                                    "task": question_text(known),
                                    "evidence": "[1] " + known["ANSWER"],
                                },
                            )
                        )
                    for category, endpoint, payload in cases:
                        started = time.perf_counter()
                        record: dict[str, Any] = {
                            "project": name,
                            "category": category,
                            "endpoint": endpoint,
                            "request": payload,
                        }
                        try:
                            response = client.post(endpoint, json=payload)
                            record["status"] = response.status_code
                            response.raise_for_status()
                            value = response.json()
                            record["response"] = value
                            if category == "answerable":
                                sources = value.get("sources", value.get("citations", []))
                                assert sources, "Official answerable question must return evidence"
                                assert all(
                                    str(s.get("source_file", s.get("source", ""))).startswith(
                                        "techqa://"
                                    )
                                    for s in sources
                                )
                                assert "streamtool" in value["answer"].casefold()
                            if category == "empty_filter":
                                assert value["refused"]
                            if category == "critic-loop":
                                assert value["retries"] <= 2 and len(value["attempts"]) <= 3
                            if category == "multi-agent":
                                assert [e["task_id"] for e in value["executions"]] == [
                                    t["task_id"] for t in value["plan"]["tasks"]
                                ]
                            record["error"] = None
                        except Exception as exc:
                            failures += 1
                            record["error"] = str(exc)
                            LOGGER.exception("%s %s failed", name, category)
                        record["latency_ms"] = (time.perf_counter() - started) * 1000
                        results.append(record)
                        LOGGER.info("%s %s error=%s", name, category, record["error"])
            finally:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)
    target = ROOT / "evals/techqa_api_smoke.json"
    target.write_text(
        json.dumps({"failures": failures, "cases": results}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return int(failures > 0)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    raise SystemExit(main())
