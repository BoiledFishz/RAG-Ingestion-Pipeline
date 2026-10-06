"""Program-derived v0.3.1 one-page report and resume record; no evaluations."""
import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from project2_v03_report import compare_tables, read, save, sha

def old_batch(folder: Path) -> dict:
    summary=read(folder/'summary.json')
    rows=[json.loads(x) for x in (folder/'requests.jsonl').read_text(encoding='utf-8').splitlines()]
    bad=[x for x in rows if x['censored']]
    details='；'.join(f"{x['sample_id']}/{x['path']}/第{x['repeat']}次/{x['elapsed_seconds']:.3f}秒" for x in bad)
    return {'batch':1,'status':summary['status'],'requests':len(rows),'expected':summary['expected'],
            'censor_reason':'用户记录的主机睡眠删失；'+details,'used_for_decision':False,
            'evidence':'evals/project2-v1/calibration_v03/summary.json'}

def comparison_text(value: dict) -> str:
    metrics=value.get('new_version') or value.get('metrics') or {}
    text=[]
    for name in ('complete','partial','count_exact','recall_at_5','recall_at_10','mrr','elapsed_seconds'):
        item=metrics.get(name)
        if not item:continue
        text.append(f"{name}={metric_text(item)}")
    for name,item in (value.get('legacy') or {}).items():
        text.append(f"{name}不支持={item['unsupported_numerator']}/{item['task_denominator']}，未启动模型，不作成本优势比较")
    noun='未完整完成' if value.get('superiority_claim') is False else '退化项'
    text.append(f"{noun}{len(value.get('regression_items',[]))}项；完整明细见summary.json")
    return '；'.join(text)


def number(value):
    return f'{value:.3f}'.rstrip('0').rstrip('.') if isinstance(value,(float,int)) else str(value)


def metric_text(item: dict) -> str:
    interval=lambda values:'['+', '.join(number(x) for x in values)+']'
    return f"{number(item.get('numerator'))}/{number(item.get('denominator'))}；均值{number(item.get('mean'))}，范围{interval(item.get('range',[]))}，95%CI {interval(item.get('ci95',[]))}"


def qa_text(summary: dict) -> str:
    text=[]
    for name in ('recall_at_5','recall_at_10','mrr','partial'):
        item=summary['metrics'][name];text.append(f"{name}: {metric_text(item)}")
    facts=summary['required_facts']
    text.append(f"待独立评分{facts['unscored_answer_observations']}份；匹配旧双评分{facts['matched_answer_observations']}份，事实覆盖仅为条件子集，不代表全体")
    for role,item in facts['metrics'].items():
        text.append(f"{role}事实覆盖(条件子集): {metric_text(item)}")
    text.append(f"相对v0退化记录{len(summary['regression_items'])}条（题目×重复×指标，非题数）")
    return '；'.join(text)


def stage_progression(completion: dict | None) -> dict:
    if not completion or not completion.get('execution_complete'):
        return {'status':'running_stage_comparison','reason':None}
    quality=completion['quality']
    if quality['acceptance']=='not_accepted':
        pending=sum(quality['pending_independent_fact_ratings'].values())
        return {'status':'stopped_s14_acceptance',
                'reason':f"批准S14未满足：tune原成功对照{quality['control_regressed_questions']}题退化；{pending}份答案仍缺独立双评分。工程门禁通过，质量未验收；本阶段held-out已消费一次，不改配置重跑，不把阶段记为完整通过或推进Chap13。"}
    return {'status':'stage_execution_recorded','reason':'执行证据完整；答案质量仍需按冻结指标审查，不能自动宣称生产验收通过。'}


def bind_gate_partial_evidence(root: Path, approved: list[dict], items: list[dict], gate: dict | None) -> list[dict]:
    """Bind machine-checked sub-scenarios; never infer whole requirement pass."""
    from summarize_project2 import stage_verdict
    if not gate or gate.get('status')!='passed' or stage_verdict(gate)!='passed':return items
    proof=root/f"audit/project2-v1/v031_ch12_gate_round{gate['repair_rounds']}.json"
    original=read(proof)
    if not original or original['checks']!=gate['checks']:raise ValueError('Gate evidence differs from immutable proof')
    evidence=proof.relative_to(root).as_posix();digest=sha(proof)
    checks={x['check'].split('(')[0]:x['check'] for x in original['checks'] if x['check'].startswith('AC')}
    source={x['requirement_id']:x for x in approved}
    scenarios={x['scenario_id']:x for x in csv.DictReader((root/'specs/project2/v0.3.1/acceptance_scenarios.csv').open(encoding='utf-8-sig',newline=''))}
    for item in items:
        ids=set(source[item['requirement_id']]['scenario_ids'].split(';'))
        matches=sorted(ids&checks.keys())
        if not matches:continue
        entries=item.setdefault('partial_evidence',[])
        for scenario in matches:
            entry={'scenario_id':scenario,'gate_check':checks[scenario],'evidence_file':evidence,
                   'evidence_sha256':digest,'evidence_type':scenarios[scenario]['planned_evidence_type'],
                   'coverage':'machine_checked_subscenario_only;not_whole_requirement_acceptance'}
            if entry not in entries:entries.append(entry)
        if evidence not in item['evidence_files']:item['evidence_files'].append(evidence)
        if item['execution_status']!='通过':
            item['execution_status']='部分'
            item['actual']='已绑定程序通过的工程子场景；其余子场景及质量条件未据此判通过'
    return items


def one_page(root: Path, report: dict) -> str:
    labels={'passed':'通过','failed':'失败','not_executed':'未执行'}
    native=report.get('native_gate');progress=report.get('native_progress')
    lines=['# Project 2 自动执行汇总','',f"程序状态：**{report['execution_status']}**。",'',
           '| 阶段 | 门禁结果 |','| --- | --- |']
    for stage in report['stages']:
        label=labels[stage['status']]
        if stage['stage']=='Chap12' and stage['report'] is None and native:
            label=f"真实子门禁{labels[native['status']]}；完整门禁未执行"
            if progress and progress['repair_round']>native['repair_rounds']:
                label=f"第{progress['repair_round']}修复轮子门禁执行中；完整门禁未执行"
        elif (stage['report'] or {}).get('comparison_and_heldout_pending'):
            label+='；阶段对照/held-out未完成'
        if (stage['report'] or {}).get('engineering_gate_only'):
            label+='（工程门禁）'
        lines.append(f"| {stage['stage']} | {label} |")
    counts=report['traceability_counts']
    lines+=['',f"追踪：通过 {counts['通过']} / 部分 {counts['部分']} / 未完成 {counts['未完成']}。held-out累计 {report['heldout_stage_calls_project2']}次阶段调用 / {report['heldout_repetitions_project2']}次重复；本地提交 {report['new_local_commits']}。",
            '', '| 对照 | 关键结果（95%CI及退化项） |','| --- | --- |']
    for entry in report['comparisons']:
        value=entry['summary'];lines.append(f"| {entry['name']} | "+('未执行' if value is None else comparison_text(value))+' |')
    if report.get('qa_summaries'):
        lines+=['','| QA质量（冻结v0对照；三重复） | 实测及限制 |','| --- | --- |']
        for partition,summary in report['qa_summaries'].items():
            lines.append(f"| {partition} | {qa_text(summary)} |")
        quality=report.get('quality_receipt') or {}
        if quality:
            lines.append(f"S14质量：{quality['acceptance']}；原成功对照退化{quality['control_regressed_questions']}题/{quality['control_regressed_question_repeats']}题次。completed服务状态不等于事实认证；改变后的答案不继承旧评分。")
    lines+=['','**标定批次**','', '| 批次 | 记录 | 状态 / 删失原因 | 决策 |','| --- | --- | --- | --- |']
    for batch in report['batches']:
        reason=batch.get('censor_reason') or '无已记录删失'
        lines.append(f"| {batch['batch']} | {batch['requests']}/300 | {batch['status']}；{reason} | {'采用' if batch['used_for_decision'] else '不采用'} |")
    decision=report.get('decision')
    if decision and decision['status']=='selected':
        limits=decision['limits'];lines.append(f"冻结上限：依赖 {limits['attempts']} / LLM {limits['llm_calls']} / {limits['seconds']:.3f}秒；批次1保留，不混合批次。")
    if native:
        q=native['n_quality'];scope='' if native['complete'] else '（该轮不完整，仅描述）'
        fmt=lambda values:'['+', '.join(number(x) for x in values)+']'
        lines.append(f"第{native['repair_rounds']}轮N拒答{scope}（非门禁）：{q['numerator']}/{q['denominator']}；聚类95%CI {fmt(q['cluster_bootstrap95'])}；三重复均值 {number(q['mean'])}、范围 {fmt(q['range'])}。失败/超时不算正确拒答，冻结v0结论不变。")
    if progress:lines.append(f"最新真实子门禁第{progress['repair_round']}轮：{progress['requests']}/{progress['expected']}；失败观察{progress['failed_observations']}。未完成不判通过。")
    lines+=['','**规格修订**','', '；'.join(f"{entry['version']}：{entry['delta_count']}处" for entry in report['revision_history'])+'。v0.3.1仅防睡眠、心跳检测、整批选择及16/6调用下限；原公式/熔断/状态矩阵不变。',
            '', '**两表一致性**','',f"{report['two_table_consistency']['status']}：批准表/运行表各{report['two_table_consistency']['approved_rows']}行，批准状态保持待实施；旧v0的{report['baseline_sut_files_unchanged']}份源码/配置哈希不变。文档检查{report['document_checks']}行PASS。",
            '', '停止原因：'+(report['stop_reason'] or '无；继续执行，尚未完成全部阶段。'),
            '本人事项：'+('完成变化答案的独立人工评分，决定未达S14的后续处理；' if (report.get('quality_receipt') or {}).get('acceptance')=='not_accepted' else '')+'git push/PR与最终审阅；第16章云账号及预算另行授权；向老师确认CL-03（Fake Publish未实施）。',
            '',f"[机器证据与CI明细](<{(root/'audit/project2-v1/summary.json').as_posix()}>) · [续跑记录](<{(root/'specs/project2/progress.md').as_posix()}>) · [规格哈希与授权](<{(root/'specs/project2/v0.3.1/approval_addendum.md').as_posix()}>)。"]
    review=root/'evals/project2-v1/ch12/independent_review/human_template.json'
    if review.exists():lines.append(f"[待独立评分模板（另存副本填写）](<{review.as_posix()}>)。")
    return '\n'.join(lines)+'\n'


def generate(root: Path) -> str:
    import summarize_project2 as prior
    docs=root/'specs/project2/v0.3.1';folder=root/'evals/project2-v1/calibration_v031';audit=root/'audit/project2-v1'
    manifest=read(docs/'version_manifest.json');p=read(folder/'protocol.json')
    for name,digest in manifest['files'].items():
        if sha(docs/name)!=digest: raise ValueError('v0.3.1 approved artifact changed: '+name)
    for name,digest in {**p['protected_files'],**p['batch1_files']}.items():
        if sha(root/name)!=digest: raise ValueError('Old specification/batch changed: '+name)
    baseline=read(root/'evals/protocol_v0/baseline_v0.config.json')
    if sha(root/'evals/protocol_v0/baseline_v0.config.json')!=p['baseline_config_sha256'] or any(sha(root/name)!=digest for name,digest in baseline['sut']['files'].items()):
        raise ValueError('Frozen baseline changed')
    batches=[old_batch(root/'evals/project2-v1/calibration_v03')]
    for number in (2,3):
        target=folder/f'batch{number}'
        if not target.exists():continue
        summary=read(target/'summary.json');raw=target/'requests.jsonl'
        count=len(raw.read_text(encoding='utf-8').splitlines()) if raw.is_file() else 0
        heartbeats=target/'heartbeats.jsonl'
        beats=[json.loads(x) for x in heartbeats.read_text(encoding='utf-8').splitlines()] if heartbeats.exists() else []
        suspended=any(x['host_suspended'] for x in beats)
        status=(summary or {}).get('status','host_suspended' if suspended else 'running')
        batches.append({'batch':number,'status':status,'requests':count,'censor_reason':(summary or {}).get('reason') or (summary or {}).get('failure'),
                        'used_for_decision':status=='selected','max_heartbeat_gap_seconds':max((x['gap_seconds'] or 0 for x in beats),default=None)})
    decision=read(folder/'decision.json');stages=[];native=None
    for n in (2,1,0):
        candidate=read(audit/f'v031_native_gate_round{n}.json')
        if candidate: native=candidate;break
    native_progress=None
    for n in (2,1,0):
        path=audit/f'v031_native_requests_round{n}.jsonl'
        if path.is_file():
            rows=[json.loads(x) for x in path.read_text(encoding='utf-8').splitlines()]
            native_progress={'repair_round':n,'requests':len(rows),'expected':(len(p['n_samples'])+2)*p['repeats'],
                             'failed_observations':sum(not x['check']['passed'] for x in rows),'records':path.relative_to(root).as_posix()}
            break
    for stage in ('Chap12','Chap13','Chap14','Chap15'):
        value=read(audit/f'v031_{stage.lower()}_gate.json')
        stages.append({'stage':stage,'status':prior.stage_verdict(value),'report':value})
    passed=[x['stage'] for x in stages if x['status']=='passed']
    state=read(audit/'execution_state.json')
    last=batches[-1];status='calibrating';reason=None
    if decision and decision['status']!='selected': status='stopped_calibration_'+decision['status'];reason='所授权批次未得到完整无删失结果；不冻结生产预算，不继续门禁。'
    elif decision:
        status='awaiting_native_gate' if not native else 'awaiting_full_gate' if native['status']=='passed' else 'repairing_native_gate'
        if native and native['status']=='failed' and native['repair_rounds']>=2:
            status='stopped_gate_failure';reason='真实组合子门禁两轮修复后仍失败：'+','.join(native['failure_items'])
        if native_progress and not read(audit/f"v031_native_gate_round{native_progress['repair_round']}.json"):
            status='running_native_gate'
        full=stages[0]['report']
        if full:
            if full['status']=='failed':
                status='repairing_full_gate'
                if full.get('chapter_repair_rounds',full['repair_rounds']+(native or {}).get('repair_rounds',0))>=2:
                    status='stopped_gate_failure';reason='完整工程门禁两轮修复后仍失败：'+','.join(full['failure_items'])
            elif full.get('comparison_and_heldout_pending'):status='running_stage_comparison'
    for stage in stages:
        value=stage['report']
        if value and value.get('stop_reason'):
            status='stopped_'+stage['stage'].lower();reason=value['stop_reason']
    completion=read(audit/'v031_ch12_completion.json')
    if completion:
        progression=stage_progression(completion)
        status,reason=progression['status'],progression['reason']
    approved=list(csv.DictReader((docs/'traceability.csv').open(encoding='utf-8-sig',newline='')))
    runtime=read(audit/'traceability_runtime.json');items=runtime['items']
    if runtime['source_sha256']!=sha(docs/'traceability.csv'):raise ValueError('Runtime source hash mismatch')
    items=bind_gate_partial_evidence(root,approved,items,stages[0]['report'])
    comparison=compare_tables(approved,items,passed)
    if comparison['status']!='passed':raise ValueError('Traceability mismatch: '+str(comparison['issues']))
    save(audit/'v031_traceability_comparison.json',comparison)
    save(audit/'traceability_runtime.json',{'source':'specs/project2/v0.3.1/traceability.csv','source_sha256':sha(docs/'traceability.csv'),'items':items})
    counts=Counter({'通过':0,'部分':0,'未完成':0})
    for item in items:counts['通过' if item['execution_status']=='通过' else '部分' if item['execution_status']=='部分' else '未完成']+=1
    held=[read(root/f'evals/project2-v1/{name}/heldout_receipt.json') for name in ('ch12','ch13','ch14','ch15')]
    held_calls=sum(x.get('heldout_stage_calls_project2',0) for x in held if x)
    held_repeats=sum(x.get('heldout_repetitions_project2',0) for x in held if x)
    delta=read(docs/'delta.json');doclog=audit/'docs_check_v031.log'
    revision_history=[]
    for version in ('v0.2','v0.3','v0.3.1'):
        d=read(root/f'specs/project2/{version}/delta.json')
        if d:
            categories=Counter(x.get('category',x.get('reason','authorized change')) for x in d['changes'])
            revision_history.append({'version':version,'delta_count':len(d['changes']),'categories':dict(categories)})
    checks=doclog.read_text(encoding='utf-8-sig').splitlines()
    doc_pass=sum(x.startswith('PASS ') for x in checks)
    if doc_pass!=11 or any(x.startswith('FAIL') for x in checks) or not any(sha(docs/'version_manifest.json') in x for x in checks):
        raise ValueError('No passing document check with current manifest')
    branch=prior.git_value(root,'branch','--show-current')
    report={'spec_version':'v0.3.1','execution_status':status,'stop_reason':reason,'batches':batches,'decision':decision,
         'stages':stages,'native_gate':native,'native_progress':native_progress,'traceability_counts':dict(counts),'two_table_consistency':comparison,
         'heldout_stage_calls_project2':held_calls,'heldout_repetitions_project2':held_repeats,'document_checks':doc_pass,
         'manifest_sha256':sha(docs/'version_manifest.json'),'spec_delta_count':len(delta['changes']),
         'operational_items':delta['operational_items'],'revision_history':revision_history,'baseline_sut_files_unchanged':len(baseline['sut']['files']),
         'new_local_commits':int(prior.git_value(root,'rev-list','--count',f"{state['base_commit']}..HEAD"))}
    report['qa_summaries']={partition:summary for partition in ('tune','held-out') if (summary:=read(root/f'evals/project2-v1/ch12/qa-{partition}/summary.json'))}
    freeze_path=root/'evals/protocol_v0/baseline_v0.quick.freeze.json'
    if sha(freeze_path)!=freeze_path.with_suffix('.json.sha256').read_text().split()[0]:raise ValueError('Baseline freeze record changed')
    report['baseline_v0_qa_metrics']={}
    for partition in report['qa_summaries']:
        path=root/f'evals/protocol_v0/runs/baseline-v0-quick/{partition}/summary.json'
        frozen=read(freeze_path)['summary_sha256']
        key=next(k for k in frozen if Path(k)==path.relative_to(root))
        if sha(path)!=frozen[key]:raise ValueError('Frozen baseline score changed')
        report['baseline_v0_qa_metrics'][partition]={'metrics':read(path)['metrics'],'source':path.relative_to(root).as_posix(),'sha256':sha(path)}
    report['quality_receipt']=(completion or {}).get('quality')
    lines=['# Project 2 自动执行汇总','',f"程序状态：**{status}**。"+(reason or '完整阶段门禁尚未全部通过。'),
           f"分支 `{branch}`；held-out累计 **{held_calls}次阶段调用 / {held_repeats}次重复**。",'',
           '| 阶段 | 完整门禁 |','| --- | --- |']
    labels={'passed':'通过','failed':'失败','not_executed':'未执行'}
    for stage in stages:
        note='；阶段对照/held-out待完成' if (stage['report'] or {}).get('comparison_and_heldout_pending') else ''
        lines.append(f"| {stage['stage']} | {labels[stage['status']]}{note} |")
    lines+=['',f"追踪：通过 **{counts['通过']}** / 部分 **{counts['部分']}** / 未完成 **{counts['未完成']}**；没有完整门禁证据的项不记通过。",'',
            '| 三类对照 | 关键结果 / CI / 退化项 |','| --- | --- |']
    comparisons=[]
    for name,path in [('原RAG / Agentic','evals/project2-v1/rag_vs_agentic/summary.json'),('单Agent / 固定Workflow / 新版本','evals/project2-v1/ch12/summary.json'),('可靠性改动前 / 后','evals/project2-v1/ch15/summary.json')]:
        value=read(root/path);comparisons.append({'name':name,'summary':value})
        lines.append(f"| {name} | "+('未执行；没有实测结论' if value is None else comparison_text(value))+' |')
    report['comparisons']=comparisons
    lines+=['','### 标定批次','', '| 批次 | 槽位记录 | 状态 | 删失原因 | 用于决策 |','| --- | --- | --- | --- | --- |']
    for batch in batches:
        lines.append(f"| {batch['batch']} | {batch['requests']}/300 | {batch['status']} | {batch.get('censor_reason') or '无已记录删失'} | {'是' if batch['used_for_decision'] else '否'} |")
    lines.append('批次1：因主机睡眠删失，未用于决策；原文件/哈希不变。不同批次不混合、不平均、不剔除单条。')
    if decision and decision['status']=='selected':
        limits=decision['limits'];lines.append(f"所选批次{decision['selected_batch']}；冻结硬上限：依赖{limits['attempts']} / LLM {limits['llm_calls']} / 墙钟{limits['seconds']:.3f}秒。")
        metrics=folder/f"batch{decision['selected_batch']}/metrics_ci.json"
        if metrics.is_file():lines.append(f"[三重复均值/范围、分子/分母与95%CI](<{metrics.as_posix()}>)。")
    else:lines.append('预算尚未选定；生产临时值90秒/16依赖/6LLM保持。')
    if native:
        n=native['n_quality'];lines.append(f"N拒答质量（非门禁）：{n['numerator']}/{n['denominator']}，按题聚类95%CI {n['cluster_bootstrap95']}；三重复均值/范围 {n['mean']}/{n['range']}。冻结v0结论不变，不宣称质量提升。")
        lines.append('真实组合子门禁：'+native['status']+'；未通过项：'+(','.join(native['failure_items']) or '无')+'。')
    if native_progress:
        lines.append(f"当前真实组合子门禁第{native_progress['repair_round']}轮：{native_progress['requests']}/{native_progress['expected']}，失败观察{native_progress['failed_observations']}；未完成不能判通过。")
    lines+=['','### 规格修订','',f"v0.3.1仅新增S08.2操作性段落（{report['spec_delta_count']}处精确插入、{report['operational_items']}项授权操作）；采用16/6调用下限。S08.1、32/12熔断、S07、场景/门禁/held-out及其余CL决定不变；旧三版和批次1保持。",
           f"文档检查{doc_pass}行PASS；manifest SHA256：`{report['manifest_sha256']}`。",'',
           '### 两表一致性','',f"程序比对 **{comparison['status']}**：批准表{comparison['approved_rows']}行、运行表{comparison['runtime_rows']}行；ID无缺失/新增/重复，批准状态与执行状态分开。冻结v0的{report['baseline_sut_files_unchanged']}份源码/配置哈希不变。",
           f"证据：[文档输出](<{doclog.as_posix()}>) · [批次协议](<{(folder/'protocol.json').as_posix()}>) · [两表比对](<{(audit/'v031_traceability_comparison.json').as_posix()}>)。新增本地提交{report['new_local_commits']}。",'',
           '需要本人处理：', '', '- 若程序报告授权范围外问题或两轮仍失败，决定后续授权；不放宽门禁。',
           '- git push / PR / 最终审阅由本人处理；第16章云账号与预算另行授权。', '- 向老师确认CL-03；Fake Publish未实施。']
    marker=lines.index('### 两表一致性')
    lines[marker:marker]=['修订记录：'+'；'.join(f"{x['version']} {x['delta_count']}处（"+', '.join(f'{k}:{v}' for k,v in x['categories'].items())+'）' for x in revision_history),'']
    detailed='\n'.join(lines)+'\n';(root/'specs/project2/summary_detailed.md').write_text(detailed,encoding='utf-8')
    markdown=one_page(root,report);(root/'specs/project2/summary.md').write_text(markdown,encoding='utf-8')
    state.update({'active_spec_version':'v0.3.1','execution_status':status,'current_stage':'Chap12','stop_reason':reason,
                 'calibration_batch':last['batch'],'calibration_progress':last['requests'],
                 'native_progress':native_progress,
                 'heldout_stage_calls_project2':held_calls,'heldout_repetitions_project2':held_repeats,
                 'updated_at':datetime.now(timezone.utc).isoformat()})
    save(audit/'execution_state.json',state);save(audit/'summary.json',report)
    progress=['# Project 2 自动执行续跑记录',f"程序更新时间：{state['updated_at']}",
           f"当前阶段：{state['current_stage']}；生效规格v0.3.1；状态：{status}",f"分支：{branch}；基准提交：{state['base_commit']}",
           f"标定批次{last['batch']}：{last['requests']}/300；批次1保留，未用于决策。协议/记录：evals/project2-v1/calibration_v031；日志audit/project2-v1/v031_calibration.log。",
           f"真实组合子门禁进度：{native_progress or '未启动'}。",
           f"held-out累计阶段/重复：{held_calls}/{held_repeats}；完整门禁通过前不得使用。",f"停止原因：{reason or '无；按授权继续'}",
           '已冻结批次不得改写或逐条补测；批次2仅睡眠无效才自动独立批次3，其他删失停止。防睡眠请求在运行器自身线程，5秒心跳；不改系统设置、不安装。',
           '原v0.1/v0.2/v0.3和批准v0.3.1冻结文件不可修改。两轮修复上限、门禁、场景及held-out规则不变。Chap16/远端/付费/系统安装不在范围。']
    (root/'specs/project2/progress.md').write_text('\n\n'.join(progress)+'\n',encoding='utf-8')
    return markdown
