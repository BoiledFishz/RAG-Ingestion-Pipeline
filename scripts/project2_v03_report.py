"""Evidence-derived v0.3 progress, summary and approved/runtime reconciliation."""
from __future__ import annotations
import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def read(path: Path) -> dict | None:
    return json.loads(path.read_text(encoding='utf-8')) if path.is_file() else None


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def compare_tables(approved: list[dict], runtime: list[dict], passed_stages: list[str]) -> dict:
    left=Counter(x['requirement_id'] for x in approved); right=Counter(x['requirement_id'] for x in runtime)
    issues=[]
    if left!=right or any(x!=1 for x in left.values()) or any(x!=1 for x in right.values()):
        issues.append('Missing/extra/duplicate requirement IDs')
    sources={x['requirement_id']:x for x in approved}
    for row in runtime:
        if row.get('source_status')!=sources.get(row['requirement_id'],{}).get('status'):
            issues.append('Approved source status differs: '+row['requirement_id'])
        if row.get('execution_status') not in {'待实施','部分','通过'}:
            issues.append('Unknown execution status: '+row['requirement_id'])
        if row.get('execution_status')=='通过' and (not row.get('evidence_files') or not row.get('gate_stages') or not set(row['gate_stages'])<=set(passed_stages)):
            issues.append('Passing item lacks evidence/system gate: '+row['requirement_id'])
    return {'status':'passed' if not issues else 'failed','approved_rows':len(approved),'runtime_rows':len(runtime),
            'id_counts_match':left==right,'issues':issues,'semantic_rule':'approved pending is design state; runtime execution state is separate; passed requires real complete gate evidence'}


def execution_status(calibration: dict | None, gate: dict | None) -> str:
    if calibration and calibration['status']=='stopped_structural_fuse': return 'stopped_calibration_fuse'
    if calibration and calibration['status']=='incomplete_censored': return 'stopped_calibration_censored'
    if not calibration: return 'calibrating'
    if gate and gate['status']=='failed' and gate.get('repair_rounds',0)>=2: return 'stopped_gate_failure'
    if not gate: return 'awaiting_native_gate'
    if not gate.get('system_gate_executed'): return 'awaiting_full_gate'
    return 'stage_passed' if gate['status']=='passed' else 'repairing_gate'


def generate(root: Path) -> str:
    import summarize_project2 as prior
    audit=root/'audit/project2-v1'; docs=root/'specs/project2/v0.3'; folder=root/'evals/project2-v1/calibration_v03'
    protocol=read(folder/'protocol.json'); manifest=read(docs/'version_manifest.json')
    if not protocol or not manifest: raise ValueError('v0.3 registration/specification not frozen')
    for name,digest in protocol['protected_files'].items():
        if sha(root/name)!=digest: raise ValueError('Protected original changed: '+name)
    for name,digest in manifest['files'].items():
        if sha(docs/name)!=digest: raise ValueError('Frozen v0.3 changed: '+name)
    calibration=read(folder/'summary.json')
    calibration_manifest=read(folder/'frozen_manifest.json')
    if calibration and (not calibration_manifest or any(sha(folder/name)!=digest for name,digest in calibration_manifest['files'].items())):
        raise ValueError('Frozen calibration evidence changed')
    baseline_path=root/'evals/protocol_v0/baseline_v0.config.json'
    if sha(baseline_path)!=protocol['baseline_config_sha256']:
        raise ValueError('Frozen baseline configuration changed')
    baseline=read(baseline_path)
    changed=[name for name,digest in baseline['sut']['files'].items() if sha(root/name)!=digest]
    if changed: raise ValueError('Frozen baseline source changed: '+str(changed))
    integrity={'status':'passed','baseline_sut_files':len(baseline['sut']['files']),
               'changed_baseline_files':changed,'protected_spec_files':len(protocol['protected_files']),
               'v03_manifest_sha256':sha(docs/'version_manifest.json'),
               'calibration_frozen_files':len((calibration_manifest or {}).get('files',{})),
               'scope':'read-only file/hash verification; not system gate or answer quality',
               'checked_at':datetime.now(timezone.utc).isoformat()}
    save(audit/'v03_final_integrity.json',integrity)
    raw=folder/'requests.jsonl'
    measured=[json.loads(x) for x in raw.read_text(encoding='utf-8').splitlines()] if raw.is_file() else []
    native=None; native_file=None
    for index in (2,1,0):
        candidate=audit/f'v03_native_gate_round{index}.json'
        if candidate.is_file(): native=read(candidate);native_file=candidate;break
    full=read(audit/'v03_chap12_gate.json')
    status=execution_status(calibration,full or native)
    stages=[]
    for name in ('Chap12','Chap13','Chap14','Chap15'):
        evidence=(full or native) if name=='Chap12' else read(audit/f'v03_{name.lower()}_gate.json')
        verdict=prior.stage_verdict(evidence)
        stages.append({'stage':name,'status':verdict,'system_gate_executed':bool(evidence and evidence.get('system_gate_executed')),
                       'gate_scope':(evidence or {}).get('gate_scope'),'report':evidence})
    approved=list(csv.DictReader((docs/'traceability.csv').open(encoding='utf-8-sig',newline='')))
    previous=read(audit/'traceability_runtime.json') or {'items':[]}
    source_hash=sha(docs/'traceability.csv')
    if previous.get('source_sha256',source_hash)!=source_hash: raise ValueError('Approved/runtime source hash differs')
    if previous['items'] and Counter(x['requirement_id'] for x in previous['items']) != Counter(x['requirement_id'] for x in approved):
        raise ValueError('Persisted runtime contains missing/extra/duplicate IDs; do not silently repair it')
    previous_items={x['requirement_id']:x for x in previous['items']}
    passed=[s['stage'] for s in stages if s['status']=='passed' and s['system_gate_executed']]
    runtime=[]
    for row in approved:
        old=previous_items.get(row['requirement_id'],{})
        evidence=old.get('evidence_files',[]); execution=old.get('execution_status','待实施')
        if execution=='通过' and (not set(old.get('gate_stages',[]))<=set(passed) or not all((root/f).is_file() for f in evidence)):
            raise ValueError('Existing runtime item falsely passes: '+row['requirement_id'])
        runtime.append({'requirement_id':row['requirement_id'],'source_status':row['status'],'execution_status':execution,
                        'actual':old.get('actual','未执行'),'evidence_files':evidence,'gate_stages':old.get('gate_stages',[]),
                        'partial_evidence':old.get('partial_evidence',[])})
    reconciliation=compare_tables(approved,runtime,passed)
    if reconciliation['status']!='passed': raise ValueError('Approved/runtime trace mismatch: '+str(reconciliation['issues']))
    save(audit/'v03_traceability_comparison.json',reconciliation)
    save(audit/'traceability_runtime.json',{'source':'specs/project2/v0.3/traceability.csv','source_sha256':source_hash,'items':runtime})
    counts=Counter({'通过':0,'部分':0,'未完成':0})
    for row in runtime: counts['通过' if row['execution_status']=='通过' else '部分' if row['execution_status']=='部分' else '未完成']+=1
    delta=read(docs/'delta.json'); state=read(audit/'execution_state.json') or {}
    reason=None
    if status=='stopped_calibration_fuse': reason='实测P95超过依赖32/LLM12熔断线；禁止扩大生产上限，RAG须先结构性精简。'
    elif status=='stopped_calibration_censored':
        censored=[x for x in measured if x['censored']]
        power=read(audit/'v03_host_power_events.json')
        interrupted='；系统睡眠/恢复事件已记录' if power else ''
        reason=f"完整标定有{len(censored)}条预算右删失{interrupted}，按冻结S08.1不选择新上限，不启动后续门禁或held-out。"
    elif status=='stopped_gate_failure': reason='v0.3门禁两轮修复后仍失败；不得继续修改或使用held-out。'
    elif status=='calibrating': reason=None
    held_receipts=[read(root/f'evals/project2-v1/{name}/heldout_receipt.json') for name in ('ch12','ch13','ch14','ch15')]
    held_calls=sum(x.get('heldout_stage_calls_project2',0) for x in held_receipts if x)
    held_repeats=sum(x.get('heldout_repetitions_project2',0) for x in held_receipts if x)
    comparisons=[]
    for name,path in [('原RAG / Agentic','evals/project2-v1/rag_vs_agentic/summary.json'),('单Agent / 固定Workflow / 新版本','evals/project2-v1/ch12/summary.json'),('可靠性改动前 / 后','evals/project2-v1/ch15/summary.json')]:
        comparisons.append({'name':name,'summary':read(root/path),'path':path})
    report={'spec_version':'v0.3','execution_status':status,'stages':stages,'traceability_counts':dict(counts),'traceability_total':len(runtime),
            'spec_revision':{'delta_count':len(delta['changes']),'changes':delta['changes'],'manifest_sha256':sha(docs/'version_manifest.json')},
            'two_table_consistency':reconciliation,'calibration':calibration,'calibration_progress':len(measured),'expected_calibration_requests':300,
            'native_gate':native,'comparisons':comparisons,'stop_reason':reason,'heldout_stage_calls_project2':held_calls,'heldout_repetitions_project2':held_repeats,
            'branch':prior.git_value(root,'branch','--show-current'),'new_local_commits':int(prior.git_value(root,'rev-list','--count',f"{state['base_commit']}..HEAD"))}
    report['censored_requests']=[{k:x[k] for k in ('path','sample_id','repeat','elapsed_seconds','attempts','llm_calls')} for x in measured if x['censored']]
    report['independent_counts']=read(audit/'v03_independent_counts.json')
    report['metrics_ci']=read(folder/'metrics_ci.json')
    report['integrity']=integrity
    state.update({'active_spec_version':'v0.3','current_stage':'Chap12','execution_status':status,'stop_reason':reason,'repair_rounds':(full or native or {}).get('repair_rounds',0),
                  'previous_v02_repair_rounds':2,'v03_authorization_date':'2026-10-05','heldout_stage_calls_project2':held_calls,
                  'heldout_repetitions_project2':held_repeats,'calibration_progress':len(measured),'updated_at':datetime.now(timezone.utc).isoformat()})
    save(audit/'execution_state.json',state);save(audit/'summary.json',report)
    labels={'passed':'通过','failed':'失败','not_executed':'未执行'}
    lines=['# Project 2 自动执行汇总','',f"**{status}**："+(reason or '完整阶段门禁尚未通过，不能宣布完成。'),f"分支：`{report['branch']}`；由 `scripts/summarize_project2.py` 从证据生成。",'',
           '| 阶段 | 门禁 | 执行范围 |','| --- | --- | --- |']
    for stage in stages:
        scope='完整系统门禁' if stage['system_gate_executed'] else '真实组合子门禁（非完整门禁）' if stage['report'] else '未执行'
        lines.append(f"| {stage['stage']} | {labels[stage['status']]} | {scope} |")
    lines+=['',f"追踪：通过 **{counts['通过']}** / 部分 **{counts['部分']}** / 未完成 **{counts['未完成']}**（共{len(runtime)}）；held-out累计 **{held_calls}次阶段调用 / {held_repeats}次重复**。",'',
            '| 对照 | 关键结果/CI/退化项 |','| --- | --- |']
    for item in comparisons:
        lines.append(f"| {item['name']} | "+('未执行；无实测指标或退化项' if item['summary'] is None else json.dumps(item['summary'],ensure_ascii=False,separators=(',',':')))+' |')
    doc_log=audit/'docs_check_v03_final.log'
    doc_lines=doc_log.read_text(encoding='utf-8-sig').splitlines() if doc_log.is_file() else []
    doc_pass=sum(line.startswith('PASS ') for line in doc_lines)
    doc_ok=doc_pass==11 and not any(line.startswith('FAIL') for line in doc_lines) and any(report['spec_revision']['manifest_sha256'] in line for line in doc_lines)
    report['document_check']={'status':'passed' if doc_ok else 'failed','pass_lines':doc_pass,'path':str(doc_log)}
    lines+=['','### 规格修订','',f"v0.3 **{len(delta['changes'])}条**限定修订：A实测预算协议；B将AC12-23分为状态一致性门禁、拒答质量指标。S07、42场景、AC12-03和v0.1/v0.2保持不变。旧AC12-01原因：`{delta['old_failure']['category']}`，依赖{delta['old_failure']['attempts']} / LLM {delta['old_failure']['llm_calls']} / {delta['old_failure']['elapsed_seconds']:.3f}秒。",
            f"文档检查：**{report['document_check']['status']}**（{doc_pass}行PASS；不等于系统通过）。[原始输出](<{doc_log.as_posix()}>)。",
            f"manifest SHA256：`{report['spec_revision']['manifest_sha256']}`。"]
    if calibration:
        lines += [f"完整标定：{calibration['requests']}/{calibration['expected']}，判定 **{calibration['status']}**。"]
        lines+=['含全部观测；因删失仅描述，不作为生产预算选值。方括号为按问题聚类bootstrap 95% CI。','',
                '| 路径（各150次） | 依赖P95 | LLM P95 | 耗时P95（秒） | 耗时均值 [CI]；三次均值范围 |',
                '| --- | --- | --- | --- | --- |']
        for path,measurement in calibration['paths'].items():
            metrics=(report['metrics_ci'] or {}).get('paths',{}).get(path)
            if metrics:
                def interval(values): return f"[{values[0]:.2f}, {values[1]:.2f}]"
                time=metrics['elapsed_seconds']
                lines.append(f"| {path} | {metrics['attempts']['p95']} {interval(metrics['attempts']['p95_cluster_bootstrap95'])} | {metrics['llm_calls']['p95']} {interval(metrics['llm_calls']['p95_cluster_bootstrap95'])} | {time['p95']:.2f} {interval(time['p95_cluster_bootstrap95'])} | {time['mean']:.2f} {interval(time['mean_cluster_bootstrap95'])}；{interval(time['repeat_mean_range'])} |")
            else:
                lines.append(f"| {path} | {measurement['p95']['attempts']} | {measurement['p95']['llm_calls']} | {measurement['p95']['elapsed_seconds']:.3f} | CI未执行 |")
        lines+=['','生产上限：'+(str(calibration['limits']) if calibration['limits'] else '未选定；原90秒 / 16依赖 / 6LLM保持。')]
        for row in report['censored_requests']:
            lines.append(f"删失：{row['sample_id']} / {row['path']} / 第{row['repeat']}次，{row['elapsed_seconds']:.3f}秒；原记录保留，不补跑。")
        if report['independent_counts']:
            item=report['independent_counts']; matched=sum(x['status']=='passed' for x in item['checks'])
            clarifications=sum(x['expected'].get('error','').startswith('clarification_required') for x in item['checks'])
            lines.append(f"独立复算比对：**{matched}/{item['expected_requests']}**，程序判定{item['status']}（{len(item['checks'])-clarifications}条计数结果、{clarifications}条澄清分支；不替代系统门禁）。")
        if report['metrics_ci']:
            lines.append(f"[完整指标：分子/分母、三重复、均值/范围、CI](<{(folder/'metrics_ci.json').as_posix()}>)；失败和睡眠耗时全部保留。")
    else: lines.append(f"标定已记录 **{len(measured)}/300**；结果未冻结，默认90/16/6保持。")
    if native:
        n=native['n_quality'];ci=n['cluster_bootstrap95']
        lines.append(f"N题拒答：{n['numerator']}/{n['denominator']}，按问题聚类bootstrap95%CI {ci}；三重复均值/范围 {n['mean']} / {n['range']}。质量不是门禁，冻结v0结论不变。")
        c=native['conformance'];lines.append(f"N状态一致性：{c['numerator']}/{c['denominator']}，Wilson95%CI {c['wilson95']}；接受明细另存，不冒充事实正确。")
    lines+=['','### 两表一致性','',f"程序比对：**{reconciliation['status']}**；批准表{reconciliation['approved_rows']}行、运行表{reconciliation['runtime_rows']}行，ID无缺失/新增/重复；批准待实施与实际执行状态分开，没有无证据的通过条目。",'',
            f"证据：[规格差异](<{(docs/'delta.md').as_posix()}>) · [标定记录](<{raw.as_posix()}>) · [两表比对](<{(audit/'v03_traceability_comparison.json').as_posix()}>)。冻结v0的{integrity['baseline_sut_files']}份源码/配置哈希未变。本地新增提交{report['new_local_commits']}；完整门禁未过不提交。",'',
            '需要本人处理：', '',
            '- 授权一个新的无主机睡眠标定批次，并保留本批全部记录；不删除删失样本或改判定条件。' if status=='stopped_calibration_censored' else '- 若触发停止，另行决定后续结构性精简或新一轮修复范围。',
            '- git push / PR / 最终审阅由用户本人处理；本范围不执行。', '- 第16章云账号与预算另行授权；向老师确认CL-03。']
    markdown='\n'.join(lines)+'\n';(root/'specs/project2/summary.md').write_text(markdown,encoding='utf-8')
    save(audit/'summary.json',report)
    progress=['# Project 2 自动执行续跑记录',f"程序更新时间：{state['updated_at']}",f"当前阶段：Chap12；生效规格v0.3；执行状态：{status}",
              f"本地分支：{report['branch']}；基准提交：{state['base_commit']}",f"held-out累计阶段调用/重复：{held_calls}/{held_repeats}",
              f"旧v0.2修复2轮证据保留；v0.3新授权后修复轮数：{state['repair_rounds']}（最多2）。",
              f"标定进度：{len(measured)}/300；协议：evals/project2-v1/calibration_v03/protocol.json；模型过程日志audit/project2-v1/v03_calibration.log。",
              f"停止原因：{reason or '无；按登记顺序执行/等待门禁'}",'续跑先读本文件及execution_state.json。'+('本批标定已完整运行并冻结，因删失停止；不得用--resume重写、删除或补测本批记录。新的标定批次须另行授权并单独登记，保留原批证据。' if status=='stopped_calibration_censored' else '未完成标定可--resume跳过已记录请求，不重新测已完成项。')+'默认预算未冻结前不可运行native gate或held-out。v0.1/v0.2/v0.3冻结文件不得修改。',
              'Chap12未完成；Chap13/14/15未开始；Chap16/远端/付费/系统安装不在范围。证据分类：真实运行、契约测试(Mock)、故障注入、未执行；不得以文档检查代替系统门禁。']
    (root/'specs/project2/progress.md').write_text('\n\n'.join(progress)+'\n',encoding='utf-8')
    return markdown
