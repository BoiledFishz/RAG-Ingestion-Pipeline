"""Offline tests use the committed official TechQA excerpts, never a generated KB."""

import os
from pathlib import Path
from uuid import uuid4

import pytest

os.environ["TECHQA_PROFILE"] = "fixture"
os.environ["TECHQA_RERANKER"] = "lexical"
os.environ["MODEL_PROVIDER"] = "demo"


@pytest.fixture
def tmp_path() -> Path:
    root = Path(__file__).resolve().parents[1]
    path = root / ".test_tmp" / uuid4().hex
    path.mkdir(parents=True)
    return path
