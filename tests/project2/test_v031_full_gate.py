import importlib.util
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]


def test_full_gate_rejects_empty_or_claimed_pass_without_native_evidence():
    path=ROOT/'scripts/run_project2_ch12_gate.py'
    spec=importlib.util.spec_from_file_location('full_gate',path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    assert m.verdict([])=='failed'
    checks=[{'check':name,'expected':True,'observed':True,'status':'passed'} for name in m.REQUIRED]
    assert m.verdict(checks)=='passed'
    checks[-1]['observed']=False
    assert m.verdict(checks)=='failed'
    assert m.verdict(checks[:-1])=='failed'

def test_two_repairs_are_shared_across_chapter12_subgates():
    path=ROOT/'scripts/run_project2_ch12_gate.py'
    spec=importlib.util.spec_from_file_location('full_gate_repairs',path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    assert m.allowed_repair(2,0) and m.allowed_repair(1,1)
    assert not m.allowed_repair(1,2) and not m.allowed_repair(2,1)
