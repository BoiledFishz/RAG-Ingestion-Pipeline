"""Finish only the pending registered homework checks, in sequence."""

from __future__ import annotations

import hashlib
import ctypes
import json
import logging
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUDIT = Path(__file__).resolve().parent
PYTHON = ROOT / ".venv312/Scripts/python.exe"
DOCKER = "C:/Program Files/Docker/Docker/resources/bin/docker.exe"
LOGGER = logging.getLogger(__name__)


def command(args: list[str], output: str) -> str:
    path = AUDIT / output
    if path.exists():
        raise FileExistsError("Never replace an execution log: " + str(path))
    LOGGER.info("Starting %s", output)
    with path.open("x", encoding="utf-8") as handle:
        result = subprocess.run(args, cwd=ROOT, stdout=handle, stderr=subprocess.STDOUT)
    if result.returncode:
        raise RuntimeError(f"{output}: exit={result.returncode}")
    LOGGER.info("Completed %s", output)
    return path.read_text(encoding="utf-8")


def main() -> None:
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_bool, ctypes.c_ulong]
    kernel.OpenProcess.restype = ctypes.c_void_p
    kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
    kernel.WaitForSingleObject.restype = ctypes.c_ulong
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    handle = kernel.OpenProcess(0x00100000, False, 17748)
    if not handle:
        raise OSError(ctypes.get_last_error(), "Cannot observe the registered inference process")
    LOGGER.info("Waiting for existing Chap11 PID 17748; no inference is restarted")
    last_count = -1
    while kernel.WaitForSingleObject(handle, 0) == 0x00000102:
        records = AUDIT / "chap11/requests.jsonl"
        count = len(records.read_text(encoding="utf-8").splitlines()) if records.exists() else 0
        if count != last_count:
            LOGGER.info("Registered comparison progress %d/234", count)
            last_count = count
        time.sleep(5)
    kernel.CloseHandle(handle)
    LOGGER.info("Original inference process exited")
    command([str(PYTHON), "scripts/correct_assignment_measurements.py"], "measurement_correction.log")
    empty = json.loads((AUDIT / "chap11/empty_retrieval.result.json").read_text(encoding="utf-8"))
    if empty["status"] != "passed" or not all(empty["checks"].values()):
        raise ValueError("Registered empty-retrieval example failed; do not select a replacement")
    paths = [
        "enterprise-ai-agent/agents/project2/service_runtime.py",
        "enterprise-ai-agent/agents/project2/cache_identity.py",
        "enterprise-ai-agent/agents/project2/budget.py",
        "enterprise-ai-agent/agents/project2/supervisor.py",
        "enterprise-ai-agent/agents/project2/batched_retrieval.py",
        "enterprise-ai-agent/agents/project2/rag_process.py",
        "enterprise-ai-agent/api/project2_main.py",
        "enterprise-ai-agent/api/project2_container_main.py",
        "enterprise-ai-agent/tools/techqa_document_query.py",
        "specs/project2/v0.3.4/version_manifest.json",
    ]
    expected = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in paths}
    command([
        DOCKER, "--context", "desktop-linux", "build", "--pull=false", "--no-cache",
        "--network=none", "-f", "containers/project2/Dockerfile", "-t",
        "techqa-project2-course:local", ".",
    ], "container_clean_build_final.log")
    code = (
        "import hashlib,json;from pathlib import Path;"
        f"names={paths!r};"
        "print(json.dumps({n:hashlib.sha256((Path('/app')/n).read_bytes()).hexdigest() "
        "for n in names}))"
    )
    actual = json.loads(command([
        DOCKER, "--context", "desktop-linux", "run", "--rm", "--network=none",
        "--entrypoint", "python", "techqa-project2-course:local", "-c", code,
    ], "container_final_source_verification.log"))
    if actual != expected:
        raise ValueError("Image does not contain the final source bytes")
    receipt = AUDIT / "container_build_receipt_gate1.json"
    with receipt.open("x", encoding="utf-8") as handle:
        json.dump({
            "build_exit_code": 0, "build_log": "audit/assignment-completion-20261007/container_clean_build_final.log",
            "sources_match": actual == expected, "sources": actual,
            "network": "none", "no_cache": True,
            "limits": {"attempts": 19, "llm_calls": 6, "seconds": 90},
        }, handle, ensure_ascii=False, indent=2)
    code = (
        "from pathlib import Path;import scripts.run_project2_container_gate as gate;"
        "gate.AUDIT=Path('audit/assignment-completion-20261007').resolve();"
        "import logging;logging.basicConfig(level=logging.INFO);raise SystemExit(gate.run(1))"
    )
    command([str(PYTHON), "-c", code], "container_gate_final.log")
    final = AUDIT / "container_gate_final"
    final.mkdir(exist_ok=False)
    (final / "gate.json").write_bytes((AUDIT / "container_gate_round1/gate.json").read_bytes())
    command([str(PYTHON), "scripts/summarize_project2.py", "--assignment"], "final_summary.log")
    LOGGER.info("All authorized local checks finished; remaining external tasks are disclosed")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    main()
