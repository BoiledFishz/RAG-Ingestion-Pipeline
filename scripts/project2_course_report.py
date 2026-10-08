"""Course-essential summary from actual gates and immutable aggregate evidence."""
from __future__ import annotations
import csv
import hashlib
import importlib.util
import json
import xml.etree.ElementTree as ET
from datetime import datetime,timezone
from pathlib import Path


def read(path):return json.loads(path.read_text(encoding='utf-8')) if path.exists() else None
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def gate_status(report):
    from scripts.summarize_project2 import stage_verdict
    if report and report.get('stage')=='Chap14':
        from scripts.run_project2_container_gate import verdict
        if verdict(report)!='passed':return 'failed'
    return stage_verdict(report)
def metric(m):
    if not m:return '未执行'
    return f"{m['mean']:.3f}（{m['numerator']:.2f}/{m['denominator']}；CI{[round(x,3) for x in m['ci95']]}；范围{[round(x,3) for x in m['range']]}）"


def generate(root):
    from project2_v033_report import atomic_text
    audit=root/'audit/project2-course-completion-20261007';prior=read(audit/'historical_v033_summary.json')
    docs=root/'specs/project2/v0.3.4'
    loader=importlib.util.spec_from_file_location('course_v034_checker',docs/'check_docs.py')
    module=importlib.util.module_from_spec(loader);loader.loader.exec_module(module)
    checks=module.validate(docs,root)
    stages=[]
    for name,path in [('Chap12',root/'audit/project2-v1/v031_chap12_gate.json'),('Chap13',root/'audit/project2-v1/v033_chap13_gate.json')]:
        gate=read(path);stages.append({'stage':name,'status':gate_status(gate),'passed':sum(x['status']=='passed' for x in gate['checks']),'total':len(gate['checks']),'evidence_file':path.relative_to(root).as_posix(),'source_sha256':sha(path)})
    for number in (14,15):
        pattern='container_gate_round*/gate.json' if number==14 else 'reliability_gate_round*/gate.json'
        proofs=sorted(audit.glob(pattern));path=proofs[-1] if proofs else None;gate=read(path) if path else None
        stages.append({'stage':f'Chap{number}','status':gate_status(gate),'passed':sum(x['status']=='passed' for x in (gate or {}).get('checks',[])),
            'total':len((gate or {}).get('checks',[])),'evidence_file':path.relative_to(root).as_posix() if path else None,'failure_items':(gate or {}).get('failure_items',[]),'repair_rounds':(gate or {}).get('repair_rounds')})
    suites=sorted(audit.glob('test_repair_round*/course_tests.json'));tests=read(suites[-1]) if suites else read(audit/'course_tests.json')
    counts=read(audit/'counts_v034.json')
    runtime=read(root/'audit/project2-v1/traceability_runtime.json')
    approved=list(csv.DictReader((docs/'traceability.csv').open(encoding='utf-8-sig',newline='')))
    assert runtime['source_sha256']==sha(docs/'traceability.csv')
    assert {x['requirement_id'] for x in approved}=={x['requirement_id'] for x in runtime['items']}
    trace_counts={'通过':0,'部分':0,'未完成':0}
    for item in runtime['items']:
        key='通过' if item['execution_status']=='通过' else '部分' if item['execution_status']=='部分' else '未完成'
        trace_counts[key]+=1
    assert sum(trace_counts.values())==len(approved)
    for distribution in prior['state_distributions'].values():
        assert set(distribution['counts'])=={'completed','partial','no_data','permission_denied','timeout','failed'}
        assert sum(distribution['counts'].values())==distribution['denominator']
    failed=next((s for s in stages[2:] if s['status'] not in {'passed','not_executed'}),None)
    complete=all(s['status']=='passed' for s in stages)
    active=next((s['stage'] for s in stages[2:] if s['status']!='passed'),'Chap15')
    reason='两轮修复后仍失败：'+','.join(failed['failure_items']) if failed and failed['repair_rounds']==2 else None
    report={'generated_at':datetime.now(timezone.utc).isoformat(),'active_spec_version':'v0.3.4','stages':stages,
        'execution_status':'stopped_gate_failure' if reason else 'engineering_stages_recorded' if complete else 'in_progress',
        'current_stage':active,'stop_reason':reason,'s14_status':prior['s14_status'],'scoring_status':'待盲评',
        'heldout_stage_calls_project2':prior['heldout_stage_calls_project2'],'heldout_repetitions_project2':prior['heldout_repetitions_project2'],
        'new_heldout_calls':0,'traceability_counts':trace_counts,'approved_rows':len(approved),'tests':tests,
        'count_verification':counts,'document_check_count':len(checks),'spec_manifest_sha256':sha(docs/'version_manifest.json'),
        'historical_metrics_source':'audit/project2-course-completion-20261007/historical_v033_summary.json',
        'historical_metrics_sha256':sha(audit/'historical_v033_summary.json'),'new_quality_improvement_claimed':False,
        'container_failure_diagnosis':read(audit/'container_gate_round2/read_only_failure_diagnosis.json'),
        'extra_experiments':'暂停','final_fact_coverage':'待人工盲评；不自动宣称通过',
        'historical_worker_failure_metrics':{key:(prior.get(key) or {}).get('worker_failures') for key in ('qa_tune','business_tune','heldout_current')},
        'chap12_qa_coverage_history':prior.get('old_worker_metrics',{}),
        'reliability_comparison':read(root/'evals/project2-v1/ch15/summary.json')}
    targeted=audit/'final_targeted_verification.xml'
    if targeted.exists():
        cases=ET.parse(targeted).getroot().findall('.//testcase')
        report['targeted_tests']={'tests':len(cases),'failures':sum(c.find('failure') is not None for c in cases),'errors':sum(c.find('error') is not None for c in cases),'skipped':sum(c.find('skipped') is not None for c in cases),'evidence_file':targeted.relative_to(root).as_posix(),'source_sha256':sha(targeted)}
    report['stop_verification']=read(audit/'final_stop_verification.json')
    lines=['# Project 2 课程必做项汇总','',f"程序状态：{report['execution_status']}；当前{active}。S14仍为**{report['s14_status']}**，Chap12未记完整通过。",'',
        '| 阶段 | 工程门禁 | 失败项 |','| --- | --- | --- |']
    for s in stages:lines.append(f"| {s['stage']} | {s['status']}；{s['passed']}/{s['total']} | {', '.join(s.get('failure_items',[])) or '—'} |")
    diagnosis=report['container_failure_diagnosis']
    if diagnosis:
        lines.append('**最终失败定位（只读）**：'+diagnosis['root_cause']+'；同run_id/保留卷/答案/数据/引用一致，缺'+str(len(diagnosis['missing_unique_trace_fields']))+'个Trace字段。两轮已用完，未修复/未重跑，Chap15未进入。')
    total=sum(p['totals']['tests'] for p in tests['projects'])
    failures=sum(p['totals']['failures']+p['totals']['errors'] for p in tests['projects'])
    lines += ['',f"现有三项目回归：{tests['status']}；{total}项，失败/错误{failures}。v0.3.4文档{len(checks)}条PASS；固定50查询数据库独立复算："+(f"{counts['numerator']}/{counts['denominator']}，{counts['status']}（RAG/LLM/向量关闭）" if counts else '未执行')+'。',
        f"追踪：通过{trace_counts['通过']} / 部分{trace_counts['部分']} / 未完成{trace_counts['未完成']}，合计{len(approved)}。工程子门禁不代替整条需求验收。held-out累计{report['heldout_stage_calls_project2']}阶段/{report['heldout_repetitions_project2']}重复，本轮新调用0。",'',
        '| 对照（历史90秒，三重复） | 结果 |','| --- | --- |',
        '| 原RAG / Agentic | '+('未执行' if prior['comparisons'][0]['summary'] is None else '已有证据，详见机器汇总')+' |']
    business=prior.get('business_tune')
    if business:
        unsupported='；'.join(f"{k}不支持{v['unsupported_numerator']}/{v['task_denominator']}" for k,v in business['legacy'].items())
        lines.append('| 单Agent / 固定Workflow / 新版本 | '+unsupported+'；新版本完整率'+metric(business['metrics']['complete'])+'。旧计数冲突保留，新DB-only检查不追溯改分 |')
    else:lines.append('| 单Agent / 固定Workflow / 新版本 | 未执行 |')
    reliability=report['reliability_comparison']
    lines.append('| 可靠性改动前 / 后 | '+('未执行' if reliability is None else '实测CI/范围/退化明细见机器汇总')+' |')
    lines+=['','| QA分区（历史同口径） | v0：R@5 / R@10 / MRR | 90秒：R@5 / R@10 / MRR |','| --- | --- | --- |']
    for partition,c in prior['same_partition_qa_comparison'].items():
        fmt=lambda x:' / '.join(metric(x[k]) for k in ('recall_at_5','recall_at_10','mrr')) if x else '未执行'
        lines.append('| '+partition+' | '+fmt(c['v0'])+' | '+fmt(c['current'])+' |')
    n=prior['n_refusal_history'];quality=prior['old_quality']
    lines+=['',f"**已知限制**：原成功对照历史退化{quality['control_regressed_questions']}题/{quality['control_regressed_question_repeats']}题次；归因{prior['regression_attribution']}。N拒答{n['numerator']}/{n['denominator']}，95%CI{[round(x,3) for x in n['cluster_bootstrap95']]}；均值{n['mean']:.3f}、范围{[round(x,3) for x in n['range']]}。completed不等于事实正确；容器迁移既有缓存不证明冷缓存SLA。",
        '**评分状态**：待盲评；旧LLM评分作废，不引用一致率。新的研究实验与评分暂停，未宣称事实质量改善。',
        '**预算历史**：90（初始签署）→37.941（旧Chap12/失败恢复记录）→90（v0.3.3及后续）。不混合成绩；依赖19/LLM6不变。','',
        '| 历史状态分布 | completed | partial | no_data | permission_denied | timeout | failed | 合计/样本 |','| --- | --- | --- | --- | --- | --- | --- | --- |']
    for name,d in prior['state_distributions'].items():
        lines.append('| '+name+' | '+' | '.join(str(d['counts'][k]) for k in ('completed','partial','no_data','permission_denied','timeout','failed'))+f" | {sum(d['counts'].values())}/{d['denominator']} |")
    lines.append('**Worker级timeout/failed（历史90秒）**：'+'；'.join(label+' '+metric(prior[key]['worker_failures']['any_worker_failed_or_timeout']) for label,key in [('QA tune','qa_tune'),('组合tune','business_tune'),('QA held-out','heldout_current')]))
    lines.append('**Chap12工程门禁覆盖范围**：QA修复前/后整体失败口径与Worker口径分别保留在机器汇总，不将partial视为事实正确。')
    lines+=['','**规格修订**：v0.3.4两处（仅字面组件/URL规则及独立数据预期），此前版本逐文件哈希未变；50任务、S07/S14、预算、CL、held-out不变。',
        '**两表一致性**：批准表/运行表requirement_id集合及源哈希一致，均'+str(len(approved))+'行；批准状态保持待实施。',
        '**标定批次**：批次1睡眠删失，原样保留；批次2完整300/300用于决策，未混合。',
        '停止原因：'+(reason or '无；按授权继续课程必做项，未完成项未记通过。'),
        '本人待办：人工盲评/最终审阅；git push/PR另行处理；第16章云账号与预算另授权；向老师确认CL-03（Fake Publish未做）。',
        f"[机器证据与CI](<{(audit/'course_summary.json').as_posix()}>) · [续跑进度](<{(root/'specs/project2/progress.md').as_posix()}>) · [新版授权/哈希](<{(docs/'approval_addendum.md').as_posix()}>)。"]
    assert len(lines)<=55
    text='\n'.join(lines)+'\n'
    short=['程序判定：**'+report['execution_status']+'**。', '',
        '| 阶段 | 工程门禁 |','| --- | --- |']
    short.extend(f"| {s['stage']} | {s['status']}，{s['passed']}/{s['total']} |" for s in stages)
    short+=['',f"**已完成的检查**：三项目回归{total}项、失败/错误{failures}；定向复验{report['targeted_tests']['tests']}项（与全套重叠，不相加）；文档{len(checks)}条PASS；关闭RAG/LLM/向量后，数据库独立复算{counts['numerator']}/{counts['denominator']}一致。",
        '**停止原因**：'+(reason or '无')+'。'+(diagnosis['root_cause']+'；缺'+str(len(diagnosis['missing_unique_trace_fields']))+'个Trace字段，答案/数据/引用保持一致。' if diagnosis else ''),
        f"**追踪**：通过{trace_counts['通过']} / 部分{trace_counts['部分']} / 未完成{trace_counts['未完成']}，合计{len(approved)}。批准表与运行表的ID集合、源哈希一致。",
        '**三类对照**：原RAG/Agentic本轮未运行；单Agent与固定Workflow各不支持'+str(business['legacy']['single_agent']['unsupported_numerator'])+'/'+str(business['legacy']['single_agent']['task_denominator'])+'题次；新版本历史完整率'+metric(business['metrics']['complete'])+'；可靠性前后对照未执行。',
        '**已知限制**：S14未通过，Chap12仅工程门禁通过；历史成功对照退化'+str(quality['control_regressed_questions'])+'题/'+str(quality['control_regressed_question_repeats'])+'题次，归因'+str(prior['regression_attribution'])+'。N拒答'+str(n['numerator'])+'/'+str(n['denominator'])+'，95%CI'+str([round(x,3) for x in n['cluster_bootstrap95']])+'。completed不等于事实正确。',
        '**同口径检索结果（历史90秒）**：'+ '；'.join(partition+' v0→当前 R@5/R@10/MRR='+ '/'.join(f"{comparison['v0'][k]['mean']:.3f}" for k in ('recall_at_5','recall_at_10','mrr'))+'→'+'/'.join(f"{comparison['current'][k]['mean']:.3f}" for k in ('recall_at_5','recall_at_10','mrr')) for partition,comparison in prior['same_partition_qa_comparison'].items())+'。分子/分母、CI和范围均保留在完整汇总。',
        '**Worker级timeout/failed**：'+'；'.join(label+' '+metric(prior[key]['worker_failures']['any_worker_failed_or_timeout']) for label,key in [('QA tune','qa_tune'),('组合tune','business_tune')])+ '。六类状态全部报告，加总与样本数一致。',
        '**评分状态**：待人工盲评；旧LLM评分作废，未引用一致率。超额检索、生成、Critic实验继续暂停。',
        '**规格与预算**：v0.3.4仅两处授权修订（字面组件/URL识别、独立数据预期），旧版哈希未变。预算90→37.941→90秒，旧成绩不混合；依赖19/LLM6不变。标定批次1睡眠删失、批次2完整300/300用于决策。',
        f"held-out累计{report['heldout_stage_calls_project2']}阶段/{report['heldout_repetitions_project2']}重复，本轮新增0；未读答案用于设计。容器已停止，卷保留；未push/PR/云部署。",
        '**本人待办**：若继续修复状态保存，需追加两轮上限之外的授权；人工盲评与最终审阅；远端提交/PR另处理；第16章云账号与预算另授权；向老师确认CL-03。', '',
        f"[完整程序汇总](<{(root/'specs/project2/summary.md').as_posix()}>) · [门禁证据](<{(audit/'container_gate_round2/gate.json').as_posix()}>) · [续跑记录](<{(root/'specs/project2/progress.md').as_posix()}>)。"]
    atomic_text(audit/'final_message.md','\n'.join(short)+'\n')
    atomic_text(audit/'course_summary.json',json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    atomic_text(root/'specs/project2/summary.md',text)
    atomic_text(root/'specs/project2/progress.md','# Project 2 课程必做项续跑\n\n'+json.dumps({k:report[k] for k in ['generated_at','active_spec_version','current_stage','execution_status','stop_reason','s14_status','heldout_stage_calls_project2','heldout_repetitions_project2','stages']},ensure_ascii=False,indent=2)+'\n\n证据：audit/project2-course-completion-20261007/course_summary.json。旧记录保留，超额实验/LLM评分暂停。续跑先读本文件；不从头重跑，不消费held-out，不改批准文件。\n')
    return text
