import importlib.util
import sys
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'enterprise-ai-agent'))


def test_v031_profile_is_preferred_and_fails_closed_if_unverified(tmp_path):
    from agents.project2.budget import read_frozen_limits
    path=tmp_path/'evals/project2-v1/calibration_v031/budget_frozen.json'
    path.parent.mkdir(parents=True)
    path.write_text('{"status":"frozen","version":"project2-v0.3.1-budget-v1","limits":{"attempts":40,"llm_calls":15,"seconds":99}}',encoding='utf-8')
    with pytest.raises(ValueError): read_frozen_limits(tmp_path)


def test_v031_activator_cannot_select_censored_batch1(tmp_path):
    path=ROOT/'scripts/project2_v031_budget.py'
    spec=importlib.util.spec_from_file_location('activate_v031',path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value)
    import json
    target=tmp_path/'evals/project2-v1/calibration_v031'
    target.mkdir(parents=True)
    (target/'decision.json').write_text(json.dumps({'status':'selected','selected_batch':1}),encoding='utf-8')
    with pytest.raises(ValueError): value.validate_selected_batch(tmp_path)
