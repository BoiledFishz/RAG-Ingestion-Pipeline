"""Actual subprocess stop/restart; never an evaluation --resume substitute."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'scripts'))


def test_process_restart_resume():
    from run_project2_ch13_gate import run_gate
    report = run_gate(ROOT, 0)
    assert report['status']=='passed', report['failure_items']
    assert report['system_gate_executed'] is True
