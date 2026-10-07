"""Machine-only v032 stop/coverage report; no evaluation or LLM scoring."""
from __future__ import annotations
import csv
import importlib.util
import json
import sys
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from project2_v03_report import read,save,sha,compare_tables
from project2_continuation_report import state_counts
STATES=('completed','partial','no_data','permission_denied','timeout','failed')

def classify_stop(gate,resumed,accounting):
    from summarize_project2 import stage_verdict
    workers=resumed.get('workers',{});usage=resumed.get('usage',{})
    exhausted=accounting.get('after',{}).get('consumed_seconds',0)>=37.941018
    predicate=(stage_verdict(gate)=='failed' and set(gate['failure_items'])=={'same_run_id','unchanged_native_answer_body'}
       and workers.get('rag',{}).get('status')=='timeout' and workers.get('database',{}).get('status')=='completed'
       and (workers['rag'].get('error') or {}).get('category')=='request_deadline_exhausted'
       and resumed.get('status')=='partial' and exhausted and accounting['numeric_limits_unchanged']
       and accounting['attempts_preserved'] and accounting['cumulative_not_reset']
       and usage.get('attempts',100)<19 and usage.get('llm_calls',100)<6)
    return {'status':'stopped_frozen_active_execution' if predicate else 'requires_code_diagnosis',
       'machine_predicate':predicate,'permission_to_increase_budget':False,'stochastic_rerun_permitted':False,
       'gate_passed':False,'repairs_used':gate['repair_rounds']}

def freeze_stop(root):
    audit=root/'audit/project2-v1';gate=read(audit/'v032_chap13_gate.json')
    folder=audit/f"ch13_v032_round{gate['repair_rounds']}"
    if read(folder/'gate.json')!=gate:raise ValueError('Immutable gate proof differs')
    response=read(folder/'resumed_response.json');accounting=read(folder/'recovery_accounting_evidence.json')
    stop=classify_stop(gate,response,accounting)
    if not stop['machine_predicate']:raise ValueError('Failure requires diagnosis, cannot declare budget stop')
    timings=read(folder/'after_restart_startup.json')
    events=read(folder/'resume_trace.json')['events']
    calls=[x for x in events if x['stage']=='dependency' and x.get('kind')=='llm']
    stop.update({'stage':'Chap13','failed_checks':gate['failure_items'],'gate_passes':sum(x['status']=='passed' for x in gate['checks']),
       'gate_total':len(gate['checks']),'limits':{'attempts':19,'llm_calls':6,'seconds':37.941018},
       'usage':response['usage'],'recovery_accounting':accounting,
       'process_launch_seconds':timings['process_launch_to_entry_seconds'],
       'process_launch_to_ready_seconds':timings['parent_launch_to_ready_seconds'],
       'index_load_seconds':timings['rag_startup']['startup_timings']['faiss_index_load_seconds'],
       'last_pending_dependency':{'kind':'llm','attempts':calls[-1]['attempts'],'llm_calls':calls[-1]['llm_calls']} if calls else None,
       'host_guard':read(folder/'power/host_guard.json'),
       'reason':'累计执行期限37.941018秒耗尽，恢复仍为RAG timeout/DB completed→partial；停机已排除。根因属于冻结期限/v0执行行为，不能改阈值或为随机性重跑门禁。',
       'proof_files':{p.relative_to(root).as_posix():sha(p) for p in [folder/'gate.json',folder/'resumed_response.json',folder/'recovery_accounting_evidence.json',folder/'resume_trace.json',folder/'after_restart_startup.json']}})
    path=audit/'v032_stop_decision.json'
    if path.exists() and read(path)!=stop:raise ValueError('Stop proof already frozen')
    if not path.exists():save(path,stop)
    return stop

def bind_partial(root,approved,items,gate):
    mapping={'AC13-01':{'real_subprocess_restart','same_run_id','completed_database_skipped','budget_not_reset'},
             'AC13-02':{'unknown_run_rejected','illegal_state_rejected','budget_not_reset','runtime_contract_tests'},
             'AC13-03':{'owner_read_resume_isolation','revocation_rechecked'},
             'AC13-04':{'runtime_contract_tests','completed_database_skipped','budget_not_reset'},
             'AC13-05':{'real_sqlite_fault_located_by_trace','parent_child_trace'},'AC13-06':{'read_only_policy_unregistered_publish'}}
    passed={x['check']:x for x in gate['checks'] if x['status']=='passed' and x['observed']==x['expected']}
    path=root/f"audit/project2-v1/ch13_v032_round{gate['repair_rounds']}/gate.json"
    lookup={x['requirement_id']:x for x in approved}
    for item in items:
        for scenario in sorted(set(lookup[item['requirement_id']]['scenario_ids'].split(';')) & mapping.keys()):
            checks=sorted(mapping[scenario]&passed.keys())
            if not checks:continue
            proof={'scenario_id':scenario,'gate_check':checks,'evidence_file':path.relative_to(root).as_posix(),
                   'evidence_sha256':sha(path),'evidence_type':sorted({passed[x]['evidence_type'] for x in checks}),
                   'coverage':'machine_checked_subscenario_only;not_whole_requirement_acceptance'}
            if proof not in item.setdefault('partial_evidence',[]):item['partial_evidence'].append(proof)
            if proof['evidence_file'] not in item['evidence_files']:item['evidence_files'].append(proof['evidence_file'])
            if item['execution_status']!='通过':item['execution_status']='部分'
    return items

def compact(value):
    if not value or value.get('mean') is None:return '未测'
    rounded=lambda values:[round(x,3) for x in values]
    return f"{value['mean']:.3f}（{value['numerator']:.3f}/{value['denominator']}；CI{rounded(value['ci95'])}；范围{rounded(value['range'])}）"

def generate(root):
    from summarize_project2 import stage_verdict,git_value
    docs=root/'specs/project2/v0.3.2';audit=root/'audit/project2-v1'
    loader=importlib.util.spec_from_file_location('current_docs_checker',docs/'check_docs.py')
    checker=importlib.util.module_from_spec(loader);loader.loader.exec_module(checker)
    checks=checker.validate(docs,root)
    (audit/'v032_docs_final.log').write_text('\n'.join(checks)+'\n',encoding='utf-8')
    authority=read(audit/'v032_authorization.json')
    if sha(root/authority['authorization_file'])!=authority['sha256']:raise ValueError('Authority differs')
    baseline=read(root/'evals/protocol_v0/baseline_v0.config.json')
    if any(sha(root/name)!=value for name,value in baseline['sut']['files'].items()):raise ValueError('Frozen baseline changed')
    gate12=read(audit/'v031_chap12_gate.json');gate13=read(audit/'v032_chap13_gate.json')
    stop=freeze_stop(root)
    approved=list(csv.DictReader((docs/'traceability.csv').open(encoding='utf-8-sig',newline='')))
    runtime=read(audit/'traceability_runtime.json')
    if runtime['source_sha256']!=sha(docs/'traceability.csv'):raise ValueError('Runtime source hash differs')
    items=bind_partial(root,approved,runtime['items'],gate13)
    consistent=compare_tables(approved,items,['Chap12'] if stage_verdict(gate12)=='passed' else [])
    if consistent['status']!='passed':raise ValueError(str(consistent['issues']))
    for item in items:
        for path in item['evidence_files']:
            if not (root/path).is_file():raise ValueError('Missing runtime evidence '+path)
    save(audit/'v032_traceability_comparison.json',consistent)
    save(audit/'traceability_runtime.json',{'source':'specs/project2/v0.3.2/traceability.csv','source_sha256':sha(docs/'traceability.csv'),'items':items})
    counts=Counter({'通过':0,'部分':0,'未完成':0})
    for x in items:counts['未完成' if x['execution_status']=='待实施' else x['execution_status']]+=1
    paths={'Chap12组合':'evals/project2-v1/ch12/business.requests.jsonl',
           'Chap12 QA修复前':'evals/project2-v1/ch12/qa-tune/requests.jsonl',
           'QA修复1（仅tune）':'evals/project2-v1/ch12/regression_repair1/requests.jsonl',
           'Chap12 held-out（历史）':'evals/project2-v1/ch12/qa-held-out/requests.jsonl'}
    states={name:state_counts(root/path) for name,path in paths.items()}
    states['N组合（历史）']=state_counts(root/'audit/project2-v1/v031_native_requests_round1.jsonl',select_n=True)
    native_folder=audit/f"ch13_v032_round{gate13['repair_rounds']}"
    current_counts=Counter(read(native_folder/f)['status'] for f in ['resumed_response.json','fault_response.json'])
    states['Chap13恢复/故障请求']={'counts':{s:current_counts[s] for s in STATES},'denominator':2,'sum_verified':sum(current_counts.values())==2}
    cover=[]
    for name in ['Chap12 QA修复前','QA修复1（仅tune）']:
        x=states[name];bad=x['counts']['failed']+x['counts']['timeout']
        from evaluation_protocol.statistics import metric
        rows=[json.loads(line) for line in (root/paths[name]).read_text(encoding='utf-8').splitlines()]
        for row in rows:row['failed_or_timeout']=int((row.get('result') or {}).get('status','failed') in {'failed','timeout'})
        cover.append({'name':name,'numerator':bad,'denominator':x['denominator'],'fraction':bad/x['denominator'],
                      'metrics':metric(rows,'failed_or_timeout',binary=True)})
    # No post-repair run exists: never present the earlier repair as current v032.
    final_tune=read(root/'evals/project2-v1/ch13_v032/qa-tune/summary.json')
    held_old=read(root/'evals/project2-v1/ch12/heldout_receipt.json')
    held_new=read(root/'evals/project2-v1/ch13_v032/heldout_receipt.json')
    held_calls=held_old['heldout_stage_calls_project2']+(held_new or {}).get('new_stage_calls',0)
    held_repeats=held_old['heldout_repetitions_project2']+(held_new or {}).get('new_repetitions',0)
    scoring=read(root/'evals/project2-v1/ch12/second_scoring/invalidation.json')
    if not scoring or scoring['agreement_eligible']:raise ValueError('Old score invalidation missing')
    for path,digest in scoring['files'].items():
        if sha(root/path)!=digest:raise ValueError('Invalidated historical score changed: '+path)
    cleanup=read(audit/'v032_idle_cleanup/result.json')
    diagnosis=read(audit/'regression_diagnosis_round2.json')
    old_quality=read(audit/'v031_ch12_completion.json')['quality']
    n_quality=read(audit/'v031_native_gate_round1.json')['n_quality']
    repairs=read(root/'evals/project2-v1/ch12/regression_repair1/summary.json')
    business=read(root/'evals/project2-v1/ch12/summary.json')
    comparisons=[]
    for partition in ('tune','held-out'):
        comparisons.append({'partition':partition,'v0':read(root/f'evals/protocol_v0/runs/baseline-v0-quick/{partition}/summary.json')['metrics'],
                            'chap12':read(root/f'evals/project2-v1/ch12/qa-{partition}/summary.json')['metrics']})
    history=[]
    for v in ['v0.2','v0.3','v0.3.1','v0.3.2']:
        d=read(root/f'specs/project2/{v}/delta.json');history.append({'version':v,'delta_count':len(d['changes'])})
    state=read(audit/'execution_state.json');branch=git_value(root,'branch','--show-current')
    report={'spec_version':'v0.3.2','generated_at':datetime.now(timezone.utc).isoformat(),'execution_status':stop['status'],
       'current_stage':'Chap13','stop_reason':stop['reason'],'stages':[
            {'stage':'Chap12','status':stage_verdict(gate12),'report':gate12,'quality':'S14未通过'},
            {'stage':'Chap13','status':stage_verdict(gate13),'report':gate13},
            {'stage':'Chap14','status':'not_executed','report':None},{'stage':'Chap15','status':'not_executed','report':None}],
       'branch':branch,'traceability_counts':dict(counts),'two_table_consistency':consistent,'native_stop':stop,
       'heldout_stage_calls_project2':held_calls,'heldout_repetitions_project2':held_repeats,'chap13_heldout_new_calls':(held_new or {}).get('new_stage_calls',0),
       'qa_engineering_gate_coverage':cover,'post_v032_smoke':final_tune,'state_distributions':states,
       'scoring_status':'待盲评','old_scoring_status':scoring['status'],'agreement_quoted':False,
       'idle_cleanup_evidence':cleanup,
       'blind_export':read(audit/'v032_blind_export_receipt.json'),'revision_history':history,
       'document_check_lines':len(checks),'spec_manifest_sha256':sha(docs/'version_manifest.json'),
       'baseline_sut_files_unchanged':len(baseline['sut']['files']),'s14_status':'未通过',
       'control_regression_old':{'questions':old_quality['control_regressed_questions'],'observations':old_quality['control_regressed_question_repeats']},
       'remaining_regression_attribution':diagnosis['primary_attribution_distribution'],'qa_case_attribution':diagnosis['qa_category_distribution'],
       'repair1_metrics':repairs['metrics'],
       'n_refusal_history':n_quality,'same_partition_qa_comparison':comparisons,
       'new_local_commits':int(git_value(root,'rev-list','--count',state['base_commit']+'..HEAD'))}
    lines=['# Project 2 自动执行汇总','',f"程序判定：**已停止于 Chap13**；分支 `{branch}`。",'',
      '| 阶段 | 门禁 |','| --- | --- |',
      f"| Chap12 | 工程{stage_verdict(gate12)}；S14未通过，未记完整通过 |",
      f"| Chap13 | failed：{stop['gate_passes']}/{stop['gate_total']}；失败 `{', '.join(stop['failed_checks'])}` |",
      '| Chap14 / Chap15 | 未执行，前置门禁未通过 |','',
      f"追踪：通过{counts['通过']} / 部分{counts['部分']} / 未完成{counts['未完成']}。held-out累计{held_calls}次阶段/{held_repeats}次重复；本次未消耗第2次授权。",
      f"**停止原因**：{stop['reason']} 调用{stop['usage']['attempts']}/19、LLM {stop['usage']['llm_calls']}/6，均未触及次数上限。",
      f"实测重启：进程入口{stop['process_launch_seconds']:.3f}s、FAISS索引加载{stop['index_load_seconds']:.3f}s、启动到就绪{stop['process_launch_to_ready_seconds']:.3f}s；已排除停机时间。两项失败分别是整体仍partial、超时无正文可验哈希。",'',
      '**Chap12 工程门禁覆盖范围**（QA failed+timeout；历史三重复，非v0.3.2复测）：','']
    lines.extend(f"- {x['name']}：{x['numerator']}/{x['denominator']}（{x['fraction']:.2%}；CI{[round(v,3) for v in x['metrics']['ci95']]}；三重复范围{[round(v,3) for v in x['metrics']['range']]}）。" for x in cover)
    lines+=['- 本轮修复后tune冒烟/对照复测：未执行；held-out、Chap14/15未执行。','',
      '| 三类对照 | 实测结果 |','| --- | --- |',
      '| 原RAG / Agentic | '+('未执行' if not (root/'evals/project2-v1/rag_vs_agentic/summary.json').is_file() else '既有结果见机器证据；本轮未复测')+' |',
      f"| 单Agent / 固定Workflow / 新版本（Chap12历史） | 前两者各不支持{business['requests']}/{business['requests']}；新版本完整率{compact(business['new_version']['complete'])}；退化/未完整{len(business['regression_items'])}题次 |",
      '| 可靠性改动前 / 后 | 未执行 |','',
      '| QA三重复：R@5 / R@10 / MRR | v0 | Chap12历史 |','| --- | --- | --- |']
    for c in comparisons:
        fmt=lambda m:' / '.join(compact(m[k]) for k in ['recall_at_5','recall_at_10','mrr'])
        lines.append(f"| {c['partition']} | {fmt(c['v0'])} | {fmt(c['chap12'])} |")
    lines.append(f"| tune修复1（历史） | {fmt(comparisons[0]['v0'])} | {fmt(repairs['metrics'])} |")
    lines+=['',f"**已知限制**：S14未通过；初始原成功对照退化{old_quality['control_regressed_questions']}题/{old_quality['control_regressed_question_repeats']}题次；修复1仍{repairs['control_regressed_questions']}题/{repairs['control_regressed_question_repeats']}题次。剩余归因{diagnosis['primary_attribution_distribution']}；completed不等于事实正确。",
      f"41个partial归因：{dict(Counter(x['category'] for x in diagnosis['qa_cases'] if x['status']=='partial'))}；DB no_data-only={diagnosis['partial_DB_no_data_only']}。新槽位修复仅契约验证；退出清理{'真实验证通过' if cleanup and cleanup['passed'] else '待真实验证'}，未称质量提升。",
      f"历史N拒答{n_quality['numerator']}/{n_quality['denominator']}，聚类95%CI {[round(x,3) for x in n_quality['cluster_bootstrap95']]}；均值{n_quality['mean']:.3f}、范围{[round(x,3) for x in n_quality['range']]}。冻结v0结论不变。",'',
      '**评分状态**：待盲评。旧LLM评分“作废：空正文、全同分、基于修复前答案”；未引用一致率，未运行新的LLM评分。']
    export=report['blind_export']
    if export:lines.append(f"盲评包：{export['nonempty_answer_groups']}份非空历史答案；{export['auto_zero_observations']}份空/失败按0登记并排除一致率。随机顺序、身份信息另存key；不能替代本轮修复后验收。")
    lines+=['','| 状态分布 | completed | partial | no_data | permission_denied | timeout | failed | 合计 |','| --- | --- | --- | --- | --- | --- | --- | --- |']
    for name,x in states.items():lines.append('| '+name+' | '+' | '.join(str(x['counts'][s]) for s in STATES)+f" | {sum(x['counts'].values())}/{x['denominator']} |")
    lines+=['', '**标定批次**：批次1保留、睡眠删失、不用于决策；批次2完整300/300并用于决策；未混合。',
      '**规格修订**：'+'；'.join(x['version']+' '+str(x['delta_count'])+'处' for x in history)+'。v0.3.2改为累计执行记账、存活上限900秒；19/6/37.941018阈值未变。',
      f"**两表一致性**：{consistent['status']}，批准/运行各{consistent['approved_rows']}行；批准文件状态未改。文档检查{len(checks)}行PASS，冻结v0的{len(baseline['sut']['files'])}个文件未改。",'',
      '本人待办：完成盲评；决定冻结执行期限下恢复仍超时的后续授权；git push/PR/最终审阅；第16章云账号与预算另行授权；向老师确认CL-03（Fake Publish未做）。',
      f"[机器证据/CI](<{(audit/'summary.json').as_posix()}>) · [失败证据](<{(audit/'v032_stop_decision.json').as_posix()}>) · [续跑记录](<{(root/'specs/project2/progress.md').as_posix()}>)。"]
    if export:lines.append(f"[盲评文件](<{(root/export['public_markdown']).as_posix()}>) · [盲评JSON](<{(root/export['public_json']).as_posix()}>)；key另存，请评分前勿打开。")
    markdown='\n'.join(lines)+'\n'
    if len(lines)>55:raise ValueError('One page limit exceeded')
    save(audit/'summary.json',report);(root/'specs/project2/summary.md').write_text(markdown,encoding='utf-8')
    (root/'specs/project2/summary_detailed.md').write_text('# Project 2 当前机器证据详情\n\n旧LLM评分作废，不引用一致率。\n\n```json\n'+json.dumps(report,ensure_ascii=False,indent=2)+'\n```\n',encoding='utf-8')
    state.update(active_spec_version='v0.3.2',current_stage='Chap13',execution_status=stop['status'],stop_reason=stop['reason'],
         heldout_stage_calls_project2=held_calls,heldout_repetitions_project2=held_repeats,updated_at=report['generated_at'])
    save(audit/'execution_state.json',state)
    progress=['# Project 2 自动执行续跑记录',f"程序更新时间：{report['generated_at']}",
      f"当前阶段Chap13；规格v0.3.2；状态{stop['status']}。分支{branch}；基准{state['base_commit']}。",
      f"已通过：Chap12工程门禁；S14未通过。当前Chap13 {stop['gate_passes']}/{stop['gate_total']}，两项失败：{stop['failed_checks']}。",
      f"停止原因：{stop['reason']} 不是旧绝对期限问题；不得为随机性重跑，不得改冻结预算。",
      f"本次授权记录：{authority['authorization_file']}；SHA256 {authority['sha256']}。已批准v0.1/0.2/0.3/0.3.1/0.3.2保持不变。",
      '证据：audit/project2-v1/ch13_v032_round0；v032_stop_decision.json；regression_diagnosis_round2.json；v032_docs_final.log；v032_traceability_comparison.json。',
      f"held-out累计{held_calls}次阶段/{held_repeats}次重复；第2次确认性运行授权尚未使用；门禁未过，未运行tune smoke及held-out。不得打开held-out正文用于设计。",
      '退化第二轮：已先归因9题和6 failed/3 timeout/41 partial；槽位修复仅契约验证；退出清理'+('真实验证通过' if cleanup and cleanup['passed'] else '待真实验证')+'。QA真实复测未执行，不宣称退化消除。117个修复1记录保留，未重跑。',
      '评分：暂停LLM；旧评分sidecar已标作废，不引用一致率；历史非空答案盲评包已导出（若receipt存在），不是修复后验收。',
      '预算仍19次依赖/6次LLM/37.941018秒；累计执行记账，停机排除；900秒存活上限已在运行前冻结。预算门禁及S07/S14/CL/held-out规则未放宽。',
      'Chap14/15未进入；Chap16、远端push/PR、付费/在线资源和系统安装不在范围。没有阶段通过不创建阶段提交。',
      '批次1删失保留、批次2完整用于决策，未重新标定或混合；停止的API/RAG进程仅本门禁启动的所有者PID。']
    (root/'specs/project2/progress.md').write_text('\n\n'.join(progress)+'\n',encoding='utf-8')
    return markdown
