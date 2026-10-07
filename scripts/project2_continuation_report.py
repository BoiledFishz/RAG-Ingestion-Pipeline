"""Continuation authority, aggregate-only reporting and six-state accounting."""
from __future__ import annotations
import hashlib
import json
from collections import Counter
from pathlib import Path

STATES = ('completed', 'partial', 'no_data', 'permission_denied', 'timeout', 'failed')


def read(path: Path):
    return json.loads(path.read_text(encoding='utf-8')) if path.is_file() else None


def authority(root: Path) -> dict | None:
    receipt = read(root/'audit/project2-v1/continuation_authorization.json')
    if not receipt:return None
    path = root/receipt['authorization_file']
    if hashlib.sha256(path.read_bytes()).hexdigest()!=receipt['sha256']:
        raise ValueError('Continuation authorization changed')
    if receipt['origin']!='direct_user_message' or receipt['s14_waived'] or not receipt['continue_ch13_ch14_ch15_with_s14_failed']:
        raise ValueError('S14 cannot be relabelled or waived')
    return receipt


def state_counts(path: Path, *, select_n=False) -> dict:
    # Held-out use, when requested, is strictly aggregate status accounting;
    # no question/answer/evidence is returned or used for any decision.
    counter = Counter({status: 0 for status in STATES});n = 0
    for line in path.read_text(encoding='utf-8').splitlines():
        record = json.loads(line)
        if select_n and record.get('cohort')!='N':continue
        state = (record.get('result') or {}).get('status')
        if state not in STATES:raise ValueError('Missing/unregistered overall state')
        counter[state]+=1;n+=1
    if sum(counter.values())!=n:raise ValueError('State counts do not sum to sample size')
    return {'denominator':n, 'counts':dict(counter), 'sum_verified':True,
            'source':path.as_posix(), 'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}


def bind_runtime_stage_evidence(root: Path, approved: list[dict], items: list[dict], gate: dict | None) -> list[dict]:
    """Only bind observed sub-scenarios; future cloud/cache work stays pending."""
    from summarize_project2 import stage_verdict
    if not gate or gate.get('stage') != 'Chap13' or not gate.get('system_gate_executed') or gate.get('gate_scope')!='system_gate':
        return items
    if not any(x.get('status')=='passed' and x.get('observed')==x.get('expected') for x in gate.get('checks', [])):
        return items
    proof = root/f"audit/project2-v1/ch13_round{gate['repair_rounds']}/gate.json"
    if read(proof) != gate:
        raise ValueError('Chap13 immutable round proof differs from reported gate')
    mapping = {
        'AC13-01': {'real_subprocess_restart', 'same_run_id', 'completed_database_skipped', 'budget_not_reset'},
        'AC13-02': {'unknown_run_rejected', 'illegal_state_rejected', 'runtime_contract_tests'},
        'AC13-03': {'owner_read_resume_isolation', 'revocation_rechecked'},
        'AC13-04': {'runtime_contract_tests', 'completed_database_skipped', 'budget_not_reset'},
        'AC13-05': {'real_sqlite_fault_located_by_trace', 'parent_child_trace'},
        'AC13-06': {'read_only_policy_unregistered_publish'},
    }
    passed = {x['check']: x for x in gate['checks'] if x['status'] == 'passed' and x['observed'] == x['expected']}
    sources = {x['requirement_id']: x for x in approved}
    for item in items:
        for scenario in sorted(set(sources[item['requirement_id']]['scenario_ids'].split(';')) & mapping.keys()):
            checks = mapping[scenario] & passed.keys()
            if not checks:continue
            entry = {'scenario_id': scenario, 'gate_check': sorted(checks),
                     'evidence_file': proof.relative_to(root).as_posix(),
                     'evidence_sha256': hashlib.sha256(proof.read_bytes()).hexdigest(),
                     'evidence_type': sorted({passed[x].get('evidence_type', '契约测试(Mock)') for x in checks}),
                     'coverage': 'machine_checked_subscenario_only;not_whole_requirement_acceptance'}
            entries = item.setdefault('partial_evidence', [])
            if entry not in entries:entries.append(entry)
            if entry['evidence_file'] not in item['evidence_files']:item['evidence_files'].append(entry['evidence_file'])
            if item['execution_status'] != '通过':
                item['execution_status'] = '部分'
                item['actual'] = 'Chap13已执行子场景已绑定；未覆盖的云/缓存/质量条件保持待实施'
    return items


def classify_runtime_stop(gate: dict, checkpoint_budget: dict, resumed: dict) -> dict:
    from summarize_project2 import stage_verdict
    rag = resumed.get('workers', {}).get('rag', {})
    usage = resumed.get('usage', {})
    predicate = (stage_verdict(gate) == 'failed'
        and gate.get('repair_rounds', 0) >= 1
        and set(gate.get('failure_items', [])) == {'same_run_id', 'unchanged_native_answer_body'}
        and resumed.get('status') == 'partial'
        and resumed.get('workers', {}).get('database', {}).get('status') == 'completed'
        and rag.get('status') == 'timeout'
        and (rag.get('error') or {}).get('category') == 'request_deadline_exhausted'
        and usage.get('absolute_deadline') == checkpoint_budget.get('absolute_deadline')
        and usage.get('attempts', -1) >= checkpoint_budget.get('attempts', 0)
        and usage.get('llm_calls', -1) >= checkpoint_budget.get('llm_calls', 0))
    return {'status': 'stopped_frozen_deadline' if predicate else 'requires_code_repair',
            'machine_predicate': predicate, 'permission_to_increase_budget': False,
            'gate_passed': False, 'repairs_used': gate.get('repair_rounds', 0)}


def freeze_runtime_stop(root: Path) -> dict:
    gate = read(root/'audit/project2-v1/v031_chap13_gate.json')
    folder = root/f"audit/project2-v1/ch13_round{gate['repair_rounds']}"
    if read(folder/'gate.json') != gate:raise ValueError('Immutable gate proof differs')
    checkpoint = read(folder/'before_restart_checkpoint.json')
    resumed = read(folder/'resumed_response.json')
    if checkpoint['run_id'] != resumed['run_id']:raise ValueError('Not the same resumed run')
    decision = classify_runtime_stop(gate, checkpoint['budget'], resumed)
    if not decision['machine_predicate']:raise ValueError('No frozen deadline stop predicate')
    trace = read(folder/'resume_trace.json')['events']
    resumed_at = next(x['timestamp'] for x in trace if x['stage'] == 'resume' and x['status'] == 'started')
    from agents.project2.budget import read_frozen_limits
    limits = read_frozen_limits(root)
    decision.update(stage='Chap13', gate_passes=sum(x['status'] == 'passed' for x in gate['checks']),
        gate_total=len(gate['checks']), frozen_limits=limits,
        original_deadline=checkpoint['budget']['absolute_deadline'],
        restart_elapsed_seconds=resumed_at-checkpoint['created_at'],
        remaining_at_resume_seconds=checkpoint['budget']['absolute_deadline']-resumed_at,
        reason='Chap13修复1轮后门禁仍失败：重启恢复耗尽原绝对期限，RAG timeout、DB completed→partial；预算被冻结，本授权不允许调整。保留失败，不进入Chap14/15，不为随机性重复门禁。',
        stop_reason_basis='machine gate and trace; maximum two repairs is an upper bound, not permission to relax a frozen budget',
        gate_sha256=hashlib.sha256((folder/'gate.json').read_bytes()).hexdigest(),
        proof_files={p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in
            (folder/'gate.json',folder/'before_restart_checkpoint.json',folder/'resumed_response.json',folder/'resume_trace.json')})
    path=root/'audit/project2-v1/ch13_stop_decision.json'
    prior=read(path)
    if prior is not None and prior != decision:raise ValueError('Stop decision already frozen')
    if prior is None:path.write_text(json.dumps(decision,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return decision


def augment(root: Path, report: dict, state: dict) -> None:
    receipt = authority(root)
    if not receipt:return
    report['continuation_authorization']=receipt
    report['regression_diagnosis']=read(root/'audit/project2-v1/regression_diagnosis.json')
    report['regression_repair_tune_only']=read(root/'evals/project2-v1/ch12/regression_repair1/summary.json')
    report['scoring_status']=read(root/'evals/project2-v1/ch12/second_scoring/summary.json')
    scoring=report['scoring_status']
    if scoring:
        folder=root/'evals/project2-v1/ch12/second_scoring'
        plan=read(folder/'plan.json')
        if scoring['plan_sha256']!=hashlib.sha256((folder/'plan.json').read_bytes()).hexdigest():
            raise ValueError('Second rating registration changed')
        if len({plan['first'],plan['second'],plan['generator']})!=3:
            raise ValueError('Judges must differ from one another and generator')
        if plan['script_sha256']!=hashlib.sha256((root/'scripts/project2_second_scoring.py').read_bytes()).hexdigest():
            raise ValueError('Frozen scorer changed')
        second=folder/(plan['second'].replace(':','_')+'.jsonl')
        hashes=[json.loads(line)['answer_sha256'] for line in second.read_text(encoding='utf-8').splitlines()]
        empty_hash=hashlib.sha256(b'').hexdigest()
        report['scoring_body_accounting']={'items':len(hashes),'empty_items':hashes.count(empty_hash),
            'source':second.relative_to(root).as_posix(),'sha256':hashlib.sha256(second.read_bytes()).hexdigest(),
            'method':'recorded answer SHA256 only; no held-out body content read for design'}
    distributions={}
    for name, path in [('Chap12组合', root/'evals/project2-v1/ch12/business.requests.jsonl'),
                       ('Chap12 tune QA', root/'evals/project2-v1/ch12/qa-tune/requests.jsonl'),
                       ('Chap12 held-out QA（仅计数）', root/'evals/project2-v1/ch12/qa-held-out/requests.jsonl')]:
        if path.is_file():distributions[name]=state_counts(path)
    report['state_distributions']=distributions
    native=root/'audit/project2-v1/v031_native_requests_round1.jsonl'
    if native.is_file():distributions['Chap12 N组合']=state_counts(native,select_n=True)
    repair=root/'evals/project2-v1/ch12/regression_repair1/requests.jsonl'
    if repair.is_file():distributions['修复1 tune/对照']=state_counts(repair)
    report['quality_status']='S14未通过；用户仅授权继续工程阶段，没有批准质量通过'
    status='authorized_continuation';reason=None;current='Chap13'
    for stage in report['stages'][1:]:
        current=stage['stage']
        if stage['status']=='failed':
            status='stopped_'+current.lower() if (stage['report'] or {}).get('stop_reason') else 'repairing_'+current.lower()
            reason=(stage['report'] or {}).get('stop_reason')
            break
        if stage['status']=='not_executed':
            status='running_'+current.lower();break
    else:
        current='Chap15';status='authorized_engineering_stages_complete_s14_failed'
    report.update(execution_status=status, stop_reason=reason, current_stage=current)
    stop=read(root/'audit/project2-v1/ch13_stop_decision.json')
    if stop:
        for name,digest in stop['proof_files'].items():
            if hashlib.sha256((root/name).read_bytes()).hexdigest()!=digest:
                raise ValueError('Frozen stop evidence changed')
        report['runtime_stop_decision']=stop
        report.update(execution_status=stop['status'],stop_reason=stop['reason'],current_stage='Chap13')
        current='Chap13'
    state.update(current_stage=current, continuation_authorization_sha256=receipt['sha256'])
