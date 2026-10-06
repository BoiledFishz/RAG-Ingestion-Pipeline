from pathlib import Path
import importlib.util

ROOT=Path(__file__).resolve().parents[2]


def module():
    spec=importlib.util.spec_from_file_location('report_v03',ROOT/'scripts/project2_v03_report.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def test_tables_match_ids_and_reject_forged_pass():
    m=module(); approved=[{'requirement_id':'A','status':'待实施'}]
    runtime=[{'requirement_id':'A','source_status':'待实施','execution_status':'部分','evidence_files':[],'gate_stages':[]}]
    assert m.compare_tables(approved,runtime,[])['status']=='passed'
    runtime[0]['execution_status']='通过'
    assert m.compare_tables(approved,runtime,[])['status']=='failed'
    runtime.append(dict(runtime[0]))
    assert m.compare_tables(approved,runtime,[])['status']=='failed'


def test_structural_fuse_stops_even_if_legacy_gate_passed():
    m=module()
    assert m.execution_status({'status':'stopped_structural_fuse'},None)=='stopped_calibration_fuse'
    assert m.execution_status({'status':'selected'},{'status':'passed','system_gate_executed':False})=='awaiting_full_gate'


def test_censored_calibration_blocks_native_progress():
    m=module()
    assert m.execution_status({'status':'incomplete_censored'},None)=='stopped_calibration_censored'
    assert m.execution_status({'status':'incomplete_censored'},
                              {'status':'passed','system_gate_executed':True})=='stopped_calibration_censored'
