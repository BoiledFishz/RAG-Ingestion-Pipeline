"""Harness resume is only an evaluation checkpoint, not Chap13 evidence."""
import importlib.util
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))

def test_resume_does_not_replace_prior_heartbeat_session(tmp_path):
    spec=importlib.util.spec_from_file_location('native_runner',ROOT/'scripts/run_project2_v031_gate.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    base=tmp_path/'power';base.mkdir();prior=base/'host_guard_active.json';prior.write_text('original session')
    selected=m.power_session(base,True)
    assert selected!=base and not selected.exists()
    selected.mkdir()
    assert m.power_session(base,True)!=selected and prior.read_text()=='original session'
