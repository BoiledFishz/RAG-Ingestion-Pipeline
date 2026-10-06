"""Operational batch rules; tests never invoke a model or modify old records."""
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))


def runner():
    name = 'project2_v031_calibration'
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / (name+'.py'))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def test_heartbeat_gap_is_a_batch_failure_not_a_filtered_row():
    m=runner()
    assert m.heartbeat_gap(100,130) is False
    assert m.heartbeat_gap(100,130.001) is True
    rows=[{'attempts':8,'llm_calls':3,'elapsed_seconds':10,'censored':False} for _ in range(300)]
    result=m.decide_batch(rows,host_suspended=True)
    assert result['status']=='host_suspended' and result['limits'] is None


def test_only_sleep_allows_the_third_batch_and_the_first_valid_batch_wins():
    m=runner()
    assert m.next_batch({'status':'host_suspended'},2)==3
    assert m.next_batch({'status':'incomplete_censored'},2) is None
    assert m.next_batch({'status':'host_suspended'},3) is None
    assert m.next_batch({'status':'selected'},2) is None


def test_full_slot_set_and_floor_are_preserved():
    m=runner()
    p=m.registration(ROOT)
    import json
    old=json.loads((ROOT/'evals/project2-v1/calibration_v03/protocol.json').read_text(encoding='utf-8'))
    for key in ('samples','n_samples','seed','paths','repeats','attempt_definition','fuse_p95','measurement_envelope'):
        assert p[key]==old[key]
    assert len(m.slots(p))==300
    rows=[{'path':path,'sample_id':sample,'repeat':repeat,'attempts':8,'llm_calls':3,
           'elapsed_seconds':10,'censored':False} for path,sample,repeat in m.slots(p)]
    assert m.decide_batch(rows,False,p)['limits']=={'attempts':16,'llm_calls':6,'seconds':15.0}
    assert m.decide_batch(rows[:-1],False,p)['limits'] is None
    rows[0]['censored']=True
    assert m.decide_batch(rows,False,p)['status']=='incomplete_censored'
    rows[0]['censored']=False
    for row in rows: row['attempts']=33
    assert m.decide_batch(rows,False,p)['status']=='stopped_structural_fuse'


def test_runner_releases_execution_state_after_failure(tmp_path):
    m=runner(); calls=[]
    with pytest.raises(RuntimeError):
        with m.HostGuard(tmp_path, execution_state=lambda flags:calls.append(flags) or 1,
                         battery_check=lambda:None, heartbeat_seconds=.01):
            raise RuntimeError('injected runner failure')
    assert calls[0]==0x80000001 and calls[-1]==0x80000000
    assert (tmp_path/'host_guard.json').exists()


def test_unplugged_stops_before_any_slot(tmp_path):
    m=runner(); calls=[]
    with pytest.raises(m.Unplugged):
        with m.HostGuard(tmp_path, execution_state=lambda flags:calls.append(flags) or 1,
                         battery_check=lambda:False):
            pytest.fail('request must not start')
    assert calls==[]
