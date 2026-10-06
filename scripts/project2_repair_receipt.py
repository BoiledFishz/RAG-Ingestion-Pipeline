"""Preserve observations and source hashes for a failed gate repair."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main() -> None:
    audit=ROOT/'audit/project2-v1'
    raw=audit/'v031_native_requests_round0.jsonl'
    rows=[json.loads(line) for line in raw.read_text(encoding='utf-8').splitlines()]
    outliers=[{'sample_id':r['sample_id'],'repeat':r['repeat'],'elapsed_seconds':r['elapsed_seconds'],
               'usage':(r.get('result') or {}).get('usage'),'check':r['check']}
              for r in rows if r['elapsed_seconds']>37.941018]
    files=[*ROOT.glob('enterprise-ai-agent/agents/project2/*.py'),ROOT/'enterprise-ai-agent/api/project2_main.py']
    receipt={'recorded_utc':datetime.now(timezone.utc).isoformat(),'repair_round':1,
       'previous_records':len(rows),'previous_sha256':hashlib.sha256(raw.read_bytes()).hexdigest(),
       'failed_gate':'v031_native_gate_round0.json','round0_finalized_incomplete':True,
       'observed_outliers':outliers,'reason':'Abort after process cancellation left a descendant and cold-start loop; no missing observation is counted as a pass.',
       'repairs':['Cancel the owned Windows process tree before closing inherited pipes.',
                  'Share readiness initialization without cancelling it for an expired waiting request; no query is sent during initialization.',
                  'Fully verify frozen configuration before service admission and deny writes/deletes for its lifetime; request caps/formula unchanged.'],
       'repair_test_evidence':'audit/project2-v1/v031_cancellation_repair.junit.xml',
       'online_files':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
       'heldout_stage_calls_project2':0,'budget_changed':False}
    path=audit/'v031_repair_round1_receipt.json'
    if path.exists():raise ValueError('Repair receipt already registered')
    path.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

if __name__=='__main__':main()
