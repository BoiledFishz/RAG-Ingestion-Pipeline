from __future__ import annotations

import importlib.util
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def checker():
    spec = importlib.util.spec_from_file_location('docs_v03', ROOT / 'specs/project2/v0.3/check_docs.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_v03_has_exact_protected_matrix_and_allowed_scope():
    output = checker().validate_revision_scope(ROOT / 'specs/project2/v0.3', ROOT)
    assert any('v0.1/v0.2' in row for row in output)


def test_v03_rejects_unapproved_s07_change(tmp_path):
    docs = tmp_path / 'docs'
    shutil.copytree(ROOT / 'specs/project2/v0.3', docs)
    path = docs / 'spec.md'
    text = path.read_text(encoding='utf-8')
    path.write_text(text.replace('| completed | completed |', '| completed | partial |', 1), encoding='utf-8')
    with pytest.raises(ValueError, match='Protected spec'):
        checker().validate_revision_scope(docs, ROOT)


def test_v03_rejects_changed_ac12_03(tmp_path):
    docs = tmp_path / 'docs'
    shutil.copytree(ROOT / 'specs/project2/v0.3', docs)
    path = docs / 'acceptance_scenarios.csv'
    path.write_text(path.read_text(encoding='utf-8').replace('"AC12-03","Chap12"', '"AC12-03","Chap13"'), encoding='utf-8')
    with pytest.raises(ValueError):
        checker().validate_revision_scope(docs, ROOT)
