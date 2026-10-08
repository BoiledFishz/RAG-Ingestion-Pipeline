"""Approved literal-component addendum is narrow and immutable."""
import importlib.util
import json
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_v034_validates_prior_versions_and_exact_data_delta():
    docs = ROOT / 'specs/project2/v0.3.4'
    spec = importlib.util.spec_from_file_location('v034_checker', docs / 'check_docs.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    checks = module.validate(docs, ROOT)
    assert any('unchanged' in line for line in checks)
    assert any('independent' in line for line in checks)
    assert all(line.startswith('PASS ') for line in checks)


def test_v034_rejects_a_budget_change(tmp_path):
    docs=ROOT/'specs/project2/v0.3.4';copy=tmp_path/'v0.3.4'
    shutil.copytree(docs,copy)
    policy=json.loads((copy/'recovery_accounting.json').read_text(encoding='utf-8'))
    policy['execution_limit_seconds']=91
    (copy/'recovery_accounting.json').write_text(json.dumps(policy),encoding='utf-8')
    spec=importlib.util.spec_from_file_location('v034_negative_checker',docs/'check_docs.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    with pytest.raises(ValueError,match='Unapproved copied file change'):
        module.validate(copy,ROOT)
