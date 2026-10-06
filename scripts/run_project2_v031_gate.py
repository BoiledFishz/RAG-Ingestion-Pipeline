"""Execute the unchanged native criteria using the selected new budget batch."""
import argparse
import logging
import json
from datetime import datetime, timezone
from pathlib import Path
from project2_v031_calibration import HostGuard, ROOT, digest, save
from project2_v031_budget import validate_selected_batch
from run_project2_v03_gate import run

def power_session(base: Path, resume: bool) -> Path:
    if not resume or not base.exists():return base
    number=1
    while base.with_name(base.name+f'_resume{number}').exists():number+=1
    return base.with_name(base.name+f'_resume{number}')


def main() -> int:
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--repair-round',type=int,required=True)
    ap.add_argument('--resume',action='store_true');args=ap.parse_args()
    validate_selected_batch(ROOT)
    folder=ROOT/'evals/project2-v1/calibration_v031'
    session=power_session(ROOT/f'audit/project2-v1/v031_native_power_round{args.repair_round}',args.resume)
    if args.resume:
        raw=ROOT/f'audit/project2-v1/v031_native_requests_round{args.repair_round}.jsonl'
        session.mkdir(parents=True)
        save(session/'interruption_receipt.json',{'evidence_type':'真实运行','resumed_utc':datetime.now(timezone.utc).isoformat(),
             'previous_record_count':len(raw.read_text(encoding='utf-8').splitlines()),'previous_records_sha256':digest(raw),
             'previous_records_bytes':raw.stat().st_size,'unrecorded_inflight_result':'unknown; execution session no longer exists',
             'inflight_attempts':None,'inflight_cost':None,'not_chap13_process_recovery_evidence':True})
    with HostGuard(session) as guard:
        result=run(ROOT,args.repair_round,args.resume,version='v0.3.1',calibration_folder=folder,prefix='v031',guard=guard)
    logging.info('native_subgate=%s failure_items=%s',result['status'],result['failure_items'])
    return 0 if result['status']=='passed' else 1


if __name__=='__main__':
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
    raise SystemExit(main())
