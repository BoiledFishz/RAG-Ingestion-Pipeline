"""Run independent project suites without colliding top-level package names."""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOGGER = logging.getLogger(__name__)


def main() -> int:
    failed = False
    for project in (ROOT, ROOT / "enterprise-ai-agent", ROOT / "agentic-rag-homework"):
        LOGGER.info("Testing %s", project.name)
        result = subprocess.run([sys.executable, "-m", "pytest"], cwd=project, check=False)
        failed |= result.returncode != 0
    return int(failed)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    raise SystemExit(main())
