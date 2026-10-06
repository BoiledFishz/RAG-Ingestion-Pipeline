import importlib.util
import shutil
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[2]


def checker():
    path=ROOT/'specs/project2/v0.3.1/check_docs.py'
    spec=importlib.util.spec_from_file_location('docs_v031',path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


def test_operational_revision_keeps_all_nonoperational_fields():
    assert checker().validate_scope(ROOT/'specs/project2/v0.3.1',ROOT)


def test_sleep_censor_rule_cannot_be_removed(tmp_path):
    docs=tmp_path/'docs';shutil.copytree(ROOT/'specs/project2/v0.3.1',docs)
    path=docs/'spec.md';text=path.read_text(encoding='utf-8')
    path.write_text(text.replace('任何包络右删失不冻结上限','删失也可冻结上限',1),encoding='utf-8')
    with pytest.raises(ValueError): checker().validate_scope(docs,ROOT)


def test_scene_or_matrix_change_cannot_pass(tmp_path):
    docs=tmp_path/'docs';shutil.copytree(ROOT/'specs/project2/v0.3.1',docs)
    path=docs/'acceptance_scenarios.csv'
    path.write_bytes(path.read_bytes()+b'\n')
    with pytest.raises(ValueError): checker().validate_scope(docs,ROOT)
