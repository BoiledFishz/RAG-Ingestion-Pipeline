"""Bounded Docker startup; reuse the existing TechQA container and persistent volume."""

from __future__ import annotations

import logging
import subprocess
import time
import urllib.error
import urllib.request

LOGGER = logging.getLogger(__name__)


def docker(*arguments: str, timeout: float = 15) -> bool:
    try:
        result = subprocess.run(
            ["docker", *arguments], timeout=timeout, check=False,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        LOGGER.warning("Docker command timed out: %s", " ".join(arguments))
        return False


def main() -> int:
    LOGGER.info("Checking Docker engine")
    if not docker("version", "--format", "{{.Server.Version}}", timeout=5):
        LOGGER.info("Starting Docker Desktop")
        docker("desktop", "start", "--detach", timeout=10)
        deadline = time.monotonic() + 45
        while not docker("version", "--format", "{{.Server.Version}}", timeout=3):
            if time.monotonic() >= deadline:
                LOGGER.error("Docker failed to start; inspect Docker Desktop's error and logs")
                return 1
            time.sleep(2)
    LOGGER.info("Starting the TechQA Qdrant container")
    if docker("container", "inspect", "techqa-qdrant"):
        started = docker("start", "techqa-qdrant", timeout=30)
    else:
        started = docker(
            "run", "-d", "--name", "techqa-qdrant", "--restart", "unless-stopped",
            "-p", "127.0.0.1:6333:6333", "-p", "127.0.0.1:6334:6334",
            "-v", "techqa-qdrant-storage:/qdrant/storage", "qdrant/qdrant:v1.18.0", timeout=300,
        )
    if not started:
        LOGGER.error("Could not start the TechQA container")
        return 1
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen("http://127.0.0.1:6333/readyz", timeout=2) as response:
                if response.status == 200:
                    LOGGER.info("Qdrant is ready")
                    return 0
        except (urllib.error.URLError, TimeoutError):
            time.sleep(1)
    LOGGER.error("Qdrant did not become ready")
    return 1


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    raise SystemExit(main())
