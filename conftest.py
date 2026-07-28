from __future__ import annotations

import os
import tempfile
from pathlib import Path
from uuid import uuid4

import pytest


def pytest_configure(config: pytest.Config) -> None:
    """Give every test run an isolated temp directory.

    Pytest's default Windows temp directory can be left with incompatible ACLs
    when tests are run from different terminals or sandboxed tools. A unique
    path avoids reusing or deleting a directory owned by another process.
    """
    if getattr(config.option, "basetemp", None) is not None:
        return

    run_id = f"aws-support-rag-{os.getpid()}-{uuid4().hex}"
    config.option.basetemp = str(Path(tempfile.gettempdir()) / run_id)
