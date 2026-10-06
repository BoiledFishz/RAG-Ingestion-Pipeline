"""Close execution from complete immutable records, keeping quality unresolved.

Engineering gates, evaluation execution and answer-quality acceptance are distinct.
This script cannot approve changed answers or fill missing human annotations.
"""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path
from project2_v031_calibration import ROOT, digest, save
from summarize_project2 import stage_verdict


def read(path: Path):
    return json.loads(path.read_text(encoding='utf-8')) if path.is_file() else None


def repetition_set(rows: list[dict], key: str, expected: set[tuple]) -> bool:
    observed=[(row[key],row['repeat']) for row in rows]
    return len(observed)==len(expected) and len(set(observed))==len(observed) and set(observed)==expected


def quality_acceptance(quality: dict, control_ids: set[str]) -> dict:
    """Apply frozen S14 requirements; execution does not imply acceptance.

    N refusal comparisons are candidate-scope proxies, not factual adjudication
    of answers over the full corpus. Missing ratings remain missing.
    """
    control_declines=[x for x in quality['tune']['regression_items'] if x['question_id'] in control_ids]
    pending={p:s['required_facts']['unscored_answer_observations'] for p,s in quality.items()}
    n_declines=[{'partition':p,**x} for p,s in quality.items() for x in s['regression_items'] if x['metric']=='n_refusal_proxy']
    predicates={'success_controls_zero_regression':not control_declines,
                'independent_required_facts_complete':not any(pending.values()),
                'n_refusal_proxy_no_regression':not n_declines}
    checks=[{'check':name,'expected':True,'observed':value,'status':'passed' if value else 'failed'} for name,value in predicates.items()]
    return {'acceptance':'not_accepted' if not all(predicates.values()) else 'recorded_requires_metric_review',
            'spec_reference':'specs/project2/v0.3.1/spec.md#s14','checks':checks,
            'control_regressions':control_declines,
            'control_regressed_questions':len({x['question_id'] for x in control_declines}),
            'control_regressed_question_repeats':len({(x['question_id'],x['repeat']) for x in control_declines}),
            'pending_independent_fact_ratings':pending,'n_refusal_proxy_regressions':n_declines,
            'heldout_regressions':quality.get('held-out',{}).get('regression_items',[]),
            'does_not_claim_production_answer_quality':True,
            'N_scope':'official candidate-corpus label; acceptance is unadjudicated in full corpus',
            'scope':'quality receipt, separate from authorized engineering gate'}


def inspect_stage(root: Path, stage: str) -> dict:
    checks=[];artifacts={};issues=[]
    def record(name: str, passed: bool):
        checks.append({'check':name,'expected':True,'observed':bool(passed),'status':'passed' if passed else 'failed'})
    def collect(path: Path):
        if not path.is_file():raise ValueError('Missing execution evidence: '+str(path))
        artifacts[path.relative_to(root).as_posix()]=digest(path)
    gate_path=root/f'audit/project2-v1/v031_chap{stage[2:]}_gate.json'
    gate=read(gate_path)
    record('full_engineering_gate',stage_verdict(gate)=='passed')
    try:
        if not gate:raise ValueError('No engineering gate')
        proof=root/f"audit/project2-v1/v031_{stage}_gate_round{gate['repair_rounds']}.json"
        collect(proof)
        original=read(proof)
        if original['checks']!=gate['checks'] or original['status']!=gate['status']:
            raise ValueError('Engineering pointer differs from immutable gate proof')
        for name in gate['evidence_files']:collect(root/name)
        folder=root/f'evals/project2-v1/{stage}'
        protocol=read(root/'evals/project2-v1/calibration_v031/protocol.json')
        summaries=read(folder/'summary.json')
        raw=folder/'business.requests.jsonl';collect(raw);collect(folder/'summary.json')
        rows=[json.loads(line) for line in raw.read_text(encoding='utf-8').splitlines()]
        expected={(s['sample_id'],r) for s in protocol['samples'] for r in (1,2,3)}
        record('registered_business_three_repeats',repetition_set(rows,'sample_id',expected) and summaries['repeats']==3 and summaries['requests']==len(rows) and summaries['request_sha256']==digest(raw))
        record('comparison_metrics_with_ci',bool(summaries['new_version']) and all('ci95' in item and 'mean' in item and 'range' in item for item in summaries['new_version'].values()))
        plan=folder/'stage.plan.json';collect(plan);collect(plan.with_suffix('.json.sha256'))
        from project2_stage_eval import verify_plan
        verify_plan(root,stage);record('frozen_stage_configuration',True)
        splits=read(root/'splits.json')
        controls=read(root/'evals/protocol_v0/controls.json')
        quality={}
        for partition in ('tune','held-out'):
            path=folder/f'qa-{partition}';raw=path/'requests.jsonl'
            collect(raw);collect(path/'summary.json');collect(path/'scored.json')
            rows=[json.loads(line) for line in raw.read_text(encoding='utf-8').splitlines()]
            summary=read(path/'summary.json');quality[partition]=summary
            wanted=set(splits['partitions'][partition]['quick_question_ids'])
            if partition=='tune':wanted.update(x['question_id'] for x in controls['records'])
            expected={(qid,r) for qid in wanted for r in (1,2,3)}
            record(partition+'_registered_three_repeats',repetition_set(rows,'question_id',expected) and summary['repeats']==3 and summary['source_sha256']==digest(raw) and summary['stage_plan_sha256']==digest(plan))
            record(partition+'_metrics_with_ci',all('ci95' in item and 'denominator' in item for item in summary['metrics'].values()))
        receipt_path=folder/'heldout_receipt.json';collect(receipt_path)
        receipt=read(receipt_path)
        record('heldout_one_invocation',receipt['status']=='completed' and receipt['heldout_stage_calls_project2']==1 and receipt['heldout_repetitions_project2']==3 and receipt['summary_sha256']==digest(folder/'qa-held-out/summary.json'))
        control_ids={x['question_id'] for x in controls['records']}
        quality_status=quality_acceptance(quality,control_ids)
    except (OSError,KeyError,ValueError,TypeError) as exc:
        record('complete_execution_evidence',False);issues.append(str(exc));quality_status={'acceptance':'not_executed'}
    return {'stage':'Chap'+stage[2:],'execution_complete':bool(checks) and all(x['observed'] for x in checks),
            'checks':checks,'issues':issues,'artifacts':artifacts,'quality':quality_status}


def close(root: Path, stage: str) -> dict:
    result=inspect_stage(root,stage)
    if not result['execution_complete']:raise ValueError('Stage execution incomplete: '+str(result['issues'])+' '+str([x['check'] for x in result['checks'] if not x['observed']]))
    target=root/f'audit/project2-v1/v031_{stage}_completion.json'
    if target.exists():raise ValueError('Stage execution already closed; no rewrite')
    save(target,result);target.with_suffix('.json.sha256').write_text(digest(target)+'\n',encoding='utf-8')
    gate_path=root/f'audit/project2-v1/v031_chap{stage[2:]}_gate.json';gate=read(gate_path)
    gate['comparison_and_heldout_pending']=False
    gate['stage_execution_completion_file']=target.relative_to(root).as_posix()
    gate['stage_execution_completion_sha256']=digest(target)
    gate['answer_quality_acceptance']=result['quality']['acceptance']
    # Retain the engineering scope: recording measurements is not passing quality.
    save(gate_path,gate)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--stage',required=True,choices=['ch12','ch13','ch14','ch15']);parser.add_argument('--close',action='store_true');parser.add_argument('--require-quality',action='store_true',help='Exit 2 when frozen S14 quality conditions are unmet; never changes engineering predicates');args=parser.parse_args()
    result=close(ROOT,args.stage) if args.close else inspect_stage(ROOT,args.stage)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    raise SystemExit(1 if not result['execution_complete'] else 2 if args.require_quality and result['quality']['acceptance']!='accepted' else 0)
