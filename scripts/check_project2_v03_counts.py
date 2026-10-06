"""Compare real combination counts against prior independent read-only preflight.

Never constructs expected counts from Worker fields. All 50 expected predicates,
counts, overlap and differences were independently computed before these calls.
"""
import json
import hashlib
from pathlib import Path


def check(root: Path, measurements_path: Path | None=None) -> dict:
    preflight_path=root/'audit/project2-v1/preflight_report.json'
    measurements_path=measurements_path or root/'evals/project2-v1/calibration_v03/requests.jsonl'
    reference=json.loads(preflight_path.read_text(encoding='utf-8'))
    if reference['worker_calls'] or reference['llm_calls'] or reference['heldout_stage_calls_project2']:
        raise ValueError('Expected counts must come from independent read-only computation')
    rows=[json.loads(x) for x in measurements_path.read_text(encoding='utf-8').splitlines()]
    checks=[]
    for row in rows:
        if row['path']!='combination':continue
        expected=reference['sample_measurements'][row['sample_id']]
        output=(row['result'] or {}).get('workers',{}).get('database',{})
        payload=output.get('payload',{})
        actual={'counts':[x['count'] for x in payload.get('groups',[])], 'predicates':[x['predicate'] for x in payload.get('groups',[])],
                'intersection':payload.get('intersection'), 'delta_a_minus_b':payload.get('delta_a_minus_b'),
                'measurement_complete':payload.get('measurement_complete')}
        if expected.get('error','').startswith('clarification_required'):
            passed=output.get('status')=='failed' and (output.get('error') or {}).get('category')=='clarification_required'
        else:
            passed=all(actual[key]==expected.get(key) for key in ('counts','predicates','intersection','delta_a_minus_b','measurement_complete'))
        checks.append({'sample_id':row['sample_id'],'repeat':row['repeat'],'expected':expected,'observed':actual,'status':'passed' if passed else 'failed'})
    complete=len(checks)==150 and len({(x['sample_id'],x['repeat']) for x in checks})==150
    return {'status':'passed' if complete and all(x['status']=='passed' for x in checks) else 'failed',
            'expected_requests':150,'observed_requests':len(checks),'complete':complete,'checks':checks,
            'evidence_type':'真实运行','preflight_sha256':hashlib.sha256(preflight_path.read_bytes()).hexdigest(),
            'raw_sha256':hashlib.sha256(measurements_path.read_bytes()).hexdigest(),'expected_source':'independent read-only official full corpus; no Worker/builder/model output'}


if __name__=='__main__':
    root=Path(__file__).resolve().parents[1]
    report=check(root)
    (root/'audit/project2-v1/v03_independent_counts.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    raise SystemExit(0 if report['status']=='passed' else 1)
