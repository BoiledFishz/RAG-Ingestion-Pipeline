"""Limited user authorization must not silently change protected contracts."""

import importlib.util
import shutil
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "specs/project2/v0.2"


def validator():
    spec = importlib.util.spec_from_file_location("project2_v02_check", DOCS / "check_docs.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_v02_scope_is_limited_to_registered_data_predicates() -> None:
    result = validator().validate(DOCS, ROOT)
    assert any("限定修订" in x for x in result)


def test_protected_matrix_edit_is_rejected(tmp_path: Path) -> None:
    copy = tmp_path / "v0.2"
    shutil.copytree(DOCS, copy, ignore=shutil.ignore_patterns("__pycache__"))
    path = copy / "spec.md"
    original = path.read_text(encoding="utf-8")
    path.write_text(original.replace("| completed | completed | partial", "| completed | partial | partial", 1), encoding="utf-8")
    with pytest.raises(ValueError):
        validator().validate(copy, ROOT)


def test_hash_rewriting_cannot_authorize_a_new_scenario(tmp_path: Path) -> None:
    copy = tmp_path / "v0.2"
    shutil.copytree(DOCS, copy, ignore=shutil.ignore_patterns("__pycache__"))
    path = copy / "acceptance_scenarios.csv"
    path.write_text(path.read_text(encoding="utf-8-sig").replace("AC12-23", "AC12-99"), encoding="utf-8-sig")
    with pytest.raises(ValueError):
        validator().validate(copy, ROOT)
