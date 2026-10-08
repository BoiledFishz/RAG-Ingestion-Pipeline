"""Generate current progress and one-page summary solely from registered evidence."""
from __future__ import annotations
import csv
import hashlib
import importlib.util
import json
import time
from uuid import uuid4
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
from project2_v03_report import read,save,sha,compare_tables
from project2_continuation_report import state_counts
from project2_v032_report import compact
from project2_v033_metrics import worker_flags
from evaluation_protocol.statistics import metric
STATES=('completed','partial','no_data','permission_denied','timeout','failed')

def atomic_text(path,text):
    temp=path.with_name(path.name+'.'+uuid4().hex+'.tmp')
    temp.write_text(text,encoding='utf-8')
    for attempt in range(5):
        try:temp.replace(path);return
        except OSError:
            if attempt==4:raise
            time.sleep(.1*(attempt+1))

def history(root):
    audit=root/'audit/project2-v1'
    p=audit/'v033_budget_history.json'
    if p.exists():
        value=read(p)
        for x in value['results']:
            if sha(root/x['file'])!=x['sha256']:raise ValueError('Historical result changed: '+x['file'])
        return value
    specs=read(root/'evals/project2-v1/calibration_v031/budget_frozen.json')
    folders=[root/'evals/project2-v1/ch12',audit/'ch13_v032_round0',audit/'ch13_round1']
    files=[p for folder in folders if folder.exists() for p in folder.rglob('*') if p.is_file() and p.suffix in {'.json','.jsonl'}]
    files += [p for p in audit.glob('v031_native*') if p.suffix in {'.json','.jsonl'}]
    files += [p for p in audit.glob('v031_ch12_extras*.json')]
    results=[{'file':p.relative_to(root).as_posix(),'sha256':sha(p),'request_budget_seconds':37.941018,'label':'预算37.941秒；历史结果，未与v033合并'} for p in sorted(set(files)) if 'second_scoring' not in p.parts and 'independent_review' not in p.parts and p.name not in {'plan.json','stage.plan.json','heldout_receipt.json','power'} and 'power' not in p.parts]
    value={'history':[{'seconds':90,'basis':'initial signed value','results':'v0.1/v0.2 pre-calibration; see original evidence'},
                      {'seconds':37.941018,'basis':'batch2 p95 ×1.5','results':'Chap12 native gate/extras/QA/business/held-out/repair1; Chap13 v031/v032 gate'},
                      {'seconds':90,'basis':'v0.3.3 max(signed90,formula)','results':'v033 records only'}],
        'results':results,'batch2_measurement_envelope':{'seconds':300,'attempts':256,'llm_calls':64},
        'baseline_v0_budget':'no Project2 request-level budget; original model settings unchanged',
        'old_frozen_budget_sha256':sha(root/'evals/project2-v1/calibration_v031/budget_frozen.json'),
        'calibration_unchanged':specs['limits']['seconds']==37.941018,'mixing_or_averaging':False}
    save(p,value);return value

def historical_worker(root,path):
    rows=[json.loads(x) for x in (root/path).read_text(encoding='utf-8').splitlines()]
    for r in rows:r.update(worker_flags(r));r['overall_failed_or_timeout']=int((r.get('result') or {}).get('status','failed') in {'failed','timeout'})
    return {'requests':len(rows),'budget_seconds':37.941018,'worker_failures':{k:metric(rows,k,binary=True) for k in ('any_worker_failed_or_timeout','rag_failed_or_timeout','database_failed_or_timeout')},'overall_failed_or_timeout':metric(rows,'overall_failed_or_timeout',binary=True)}

def generate(root):
    from summarize_project2 import stage_verdict,git_value
    audit=root/'audit/project2-v1';docs=root/'specs/project2/v0.3.3';evals=root/'evals/project2-v1/ch13_v033'
    loader=importlib.util.spec_from_file_location('v033_checker',docs/'check_docs.py');m=importlib.util.module_from_spec(loader);loader.loader.exec_module(m)
    checks=m.validate(docs,root);atomic_text(audit/'v033_docs_final.log','\n'.join(checks)+'\n')
    authority=read(audit/'v033_authorization.json');assert sha(root/authority['authorization_file'])==authority['sha256']
    baseline=read(root/'evals/protocol_v0/baseline_v0.config.json')
    assert all(sha(root/f)==v for f,v in baseline['sut']['files'].items())
    old12=read(audit/'v031_chap12_gate.json');wall=read(audit/'v033_wall_gate_round1/gate.json') or read(audit/'v033_wall_gate/gate.json');gate13=read(audit/'v033_chap13_gate.json')
    if gate13:
        from run_project2_ch13_gate import REQUIRED
        assert {x['check'] for x in gate13['checks']}==REQUIRED and len(gate13['checks'])==len(REQUIRED)
    stages=[{'stage':'Chap12','status':stage_verdict(old12),'s14_status':'未通过','wall_recheck':wall and wall['status']},
            {'stage':'Chap13','status':stage_verdict(gate13),'passed':sum(x['status']=='passed' for x in (gate13 or {}).get('checks',[])),'total':len((gate13 or {}).get('checks',[]))}]
    stages += [{'stage':f'Chap{i}','status':stage_verdict(read(audit/f'v033_chap{i}_gate.json'))} for i in (14,15)]
    tune=read(evals/'qa-tune/summary.json');business=read(evals/'business/summary.json');held=read(evals/'qa-held-out/summary.json')
    receipt=read(evals/'heldout_receipt.json');oldheld=read(root/'evals/project2-v1/ch12/heldout_receipt.json')
    held_calls=oldheld['heldout_stage_calls_project2']+(receipt or {}).get('new_stage_calls',0)
    held_reps=oldheld['heldout_repetitions_project2']+(receipt or {}).get('new_repetitions',0)
    reason=None;stage='Chap13';execution='in_progress'
    if wall and wall['status']!='passed':reason='Chap12 90秒墙钟子门禁失败';stage='Chap12'
    elif gate13 and stage_verdict(gate13)!='passed':reason='Chap13门禁失败：'+', '.join(gate13['failure_items'])
    elif tune and not tune['smoke_passed']:reason='tune QA Worker级别failed/timeout超过10%，停止；不消耗held-out'
    elif business and not business['smoke_passed']:reason='tune组合 Worker级别failed/timeout超过10%，停止；不消耗held-out'
    feasibility_file=audit/'container_feasibility_after_start.json'
    if not feasibility_file.exists():feasibility_file=audit/'container_feasibility.json'
    feasibility=read(feasibility_file)
    if feasibility and feasibility['status']=='blocked' and stages[2]['status']=='not_executed':
        stages[2].update(status='blocked',gate_status='not_run',prerequisite_evidence=feasibility_file.relative_to(root).as_posix())
    if not reason and held and feasibility and feasibility['status']=='blocked':reason=feasibility['reason'];stage='Chap14'
    if reason:execution='stopped'
    approved=list(csv.DictReader((docs/'traceability.csv').open(encoding='utf-8-sig',newline='')))
    runtime=read(audit/'traceability_runtime.json');assert runtime['source_sha256']==sha(docs/'traceability.csv')
    items=runtime['items']
    mapping={'AC13-01':{'real_subprocess_restart','same_run_id','completed_database_skipped','budget_not_reset'},'AC13-02':{'unknown_run_rejected','illegal_state_rejected','budget_not_reset','runtime_contract_tests'},'AC13-03':{'owner_read_resume_isolation','revocation_rechecked'},'AC13-04':{'runtime_contract_tests','completed_database_skipped','budget_not_reset'},'AC13-05':{'real_sqlite_fault_located_by_trace','parent_child_trace'},'AC13-06':{'read_only_policy_unregistered_publish'}}
    lookup={x['requirement_id']:x for x in approved}
    for item in items:
        for sid in set(lookup[item['requirement_id']]['scenario_ids'].split(';'))&mapping.keys():
            passed=[x['check'] for x in (gate13 or {}).get('checks',[]) if x['status']=='passed' and x['check'] in mapping[sid]]
            if passed:
                path=audit/f"ch13_v033_round{gate13['repair_rounds']}/gate.json"
                detail=[{'check':x['check'],'evidence_type':x['evidence_type'],
                         'evidence_file':x['evidence_file'],
                         'evidence_sha256':sha(root/x['evidence_file'])}
                        for x in gate13['checks'] if x['check'] in passed]
                proof={'scenario_id':sid,'gate_check':sorted(passed),'evidence_file':path.relative_to(root).as_posix(),
                       'evidence_sha256':sha(path),'check_evidence':detail,'coverage':'subscenario_only'}
                # Runtime annotations are derived data; preserve the gate artifact
                # and replace only this version's former aggregate classification.
                item['partial_evidence']=[p for p in item.get('partial_evidence',[])
                    if not (p.get('scenario_id')==sid and p.get('evidence_file')==proof['evidence_file'])]
                item['partial_evidence'].append(proof)
                if item['execution_status']=='待实施':item['execution_status']='部分'
        if wall and wall['status']=='passed':
            for sid in {'AC12-05','AC12-16'}&set(lookup[item['requirement_id']]['scenario_ids'].split(';')):
                wall_path=audit/('v033_wall_gate_round1/gate.json' if (audit/'v033_wall_gate_round1/gate.json').exists() else 'v033_wall_gate/gate.json')
                proof={'scenario_id':sid,'evidence_file':wall_path.relative_to(root).as_posix(),'evidence_sha256':sha(wall_path),'evidence_type':'故障注入','coverage':'wall_only;budget90'}
                if proof not in item.setdefault('partial_evidence',[]):item['partial_evidence'].append(proof)
    consistent=compare_tables(approved,items,[x['stage'] for x in stages if x['status']=='passed']);assert consistent['status']=='passed',consistent
    for item in items:
        for p in item['evidence_files']:assert (root/p).is_file()
        for proof in item.get('partial_evidence',[]):
            # Older component receipts recorded a file path without a hash.
            # Add a current file-integrity observation, not a retroactive signature.
            if 'evidence_sha256' not in proof:
                proof['evidence_sha256']=sha(root/proof['evidence_file'])
                proof['hash_provenance']='v033 current file-integrity observation; older receipt was unsigned'
            assert sha(root/proof['evidence_file'])==proof['evidence_sha256']
    save(audit/'v033_traceability_comparison.json',consistent)
    save(audit/'traceability_runtime.json',{'source':'specs/project2/v0.3.3/traceability.csv','source_sha256':sha(docs/'traceability.csv'),'items':items})
    counts=Counter({'通过':0,'部分':0,'未完成':0})
    for x in items:counts['未完成' if x['execution_status']=='待实施' else x['execution_status']]+=1
    oldquality=read(audit/'v031_ch12_completion.json')['quality'];n=read(audit/'v031_native_gate_round1.json')['n_quality']
    diagnosis=read(audit/'regression_diagnosis.json');diagnosis2=read(audit/'regression_diagnosis_round2.json')
    invalid=read(root/'evals/project2-v1/ch12/second_scoring/invalidation.json');assert not invalid['agreement_eligible']
    oldpaths={'Chap12组合37.941':'evals/project2-v1/ch12/business.requests.jsonl','Chap12 QA修复前37.941':'evals/project2-v1/ch12/qa-tune/requests.jsonl','QA修复1历史37.941':'evals/project2-v1/ch12/regression_repair1/requests.jsonl','Chap12 held-out历史37.941':'evals/project2-v1/ch12/qa-held-out/requests.jsonl'}
    states={name:state_counts(root/p) for name,p in oldpaths.items()}
    states['历史N组合37.941']=state_counts(audit/'v031_native_requests_round1.jsonl',select_n=True)
    for label,data in [('QA tune90',tune),('组合tune90',business),('held-out90',held)]:
        if data:states[label]={'counts':data['state_distribution'],'denominator':data['requests'],'sum_verified':sum(data['state_distribution'].values())==data['requests']}
    assert all(x['sum_verified'] for x in states.values())
    oldworker={name:historical_worker(root,p) for name,p in oldpaths.items() if 'held-out' not in name}
    history_data=history(root);export=read(audit/'v033_blind_export_receipt.json')
    revisions=[{'version':v,'delta_count':len(read(root/f'specs/project2/{v}/delta.json')['changes'])} for v in ('v0.2','v0.3','v0.3.1','v0.3.2','v0.3.3')]
    comparison={p:{'v0':read(root/f'evals/protocol_v0/runs/baseline-v0-quick/{p}/summary.json')['metrics'],'current':(tune if p=='tune' else held) and (tune if p=='tune' else held)['metrics']} for p in ('tune','held-out')}
    report={'spec_version':'v0.3.3','generated_at':datetime.now(timezone.utc).isoformat(),'current_stage':stage,'execution_status':execution,'stop_reason':reason,'stages':stages,'traceability_counts':dict(counts),'two_table_consistency':consistent,'budget_history':history_data,'heldout_stage_calls_project2':held_calls,'heldout_repetitions_project2':held_reps,'qa_tune':tune,'business_tune':business,'heldout_current':held,'state_distributions':states,'old_worker_metrics':oldworker,'scoring_status':'待盲评','old_scoring_status':invalid['status'],'agreement_quoted':False,'blind_export':export,'s14_status':'未通过','old_quality':oldquality,'n_refusal_history':n,'regression_attribution':diagnosis.get('primary_attribution_distribution',diagnosis2['primary_attribution_distribution']),'remaining_regression_attribution':diagnosis2['primary_attribution_distribution'],'same_partition_qa_comparison':comparison,'revision_history':revisions,'baseline_sut_files_unchanged':len(baseline['sut']['files'])}
    report['count_discrepancy']=read(audit/'v033_count_discrepancy.json')
    report['container_feasibility']=feasibility
    report['container_feasibility_file']=feasibility_file.relative_to(root).as_posix() if feasibility else None
    report['container_feasibility_sha256']=sha(feasibility_file) if feasibility else None
    checkpoint=read(audit/'v033_local_commit_receipt.json')
    report['local_checkpoint']=checkpoint
    report['comparisons']=[]
    for name,relative in [('原RAG / Agentic','evals/project2-v1/rag_vs_agentic/summary.json'),
                          ('单Agent / 固定Workflow / 新版本','evals/project2-v1/ch13_v033/business/summary.json'),
                          ('可靠性改动前 / 后','evals/project2-v1/ch15/summary.json')]:
        value=read(root/relative)
        report['comparisons'].append({'name':name,'summary':value,
            'status':'未执行' if value is None else '真实运行记录（不等于质量验收）',
            'evidence_file':relative if value is not None else None,
            'source_sha256':sha(root/relative) if value is not None else None})
    branch=git_value(root,'branch','--show-current');state=read(audit/'execution_state.json')
    state.update(active_spec_version='v0.3.3',current_stage=stage,execution_status=execution,stop_reason=reason,heldout_stage_calls_project2=held_calls,heldout_repetitions_project2=held_reps,branch=branch,updated_at=report['generated_at'])
    state['evaluation_progress']={}
    for name,total in [('qa-tune',117),('business',150),('qa-held-out',90)]:
        path=evals/name/'requests.jsonl'
        if path.exists():
            # Record counts only; no held-out answer diagnosis or output.
            count=sum(1 for line in path.read_bytes().splitlines() if line.strip())
            state['evaluation_progress'][name]={'completed_slots':count,'expected_slots':total,'file':path.relative_to(root).as_posix()}
    lines=['# Project 2 自动执行汇总','',f"程序判定：{execution}；当前{stage}；分支 `{branch}`。",'', '| 阶段 | 门禁 |','| --- | --- |',f"| Chap12 | 工程{stages[0]['status']}；90秒墙钟复验{(wall or {}).get('status','未执行')}；S14未通过 |",f"| Chap13 | {stages[1]['status']} {stages[1]['passed']}/{stages[1]['total']}；失败项{(gate13 or {}).get('failure_items',[])} |",f"| Chap14 / Chap15 | {stages[2]['status']} / {stages[3]['status']} |",'',f"追踪：通过{counts['通过']} / 部分{counts['部分']} / 未完成{counts['未完成']}；held-out累计{held_calls}次阶段/{held_reps}次重复。",f"停止原因：{reason or '无；流程执行中'}。",'', '**预算历史**：90秒（最初签署）→37.941018秒（批次2公式；Chap12全部生产门禁/对照/held-out/修复1、Chap13旧门禁）→90秒（v0.3.3本轮）。旧结果逐文件哈希保留，未混合；标定观测包络300秒，v0原RAG无P2总预算。19次依赖/6次LLM/900秒存活不变。','', '**Worker级别 failed/timeout**（分子为至少一个Worker失败；含overall partial）：']
    lines[-1]+='以下CI均为95%；各配置三次重复。'
    lines.append('')
    for label,data in [('QA tune90',tune),('组合tune90',business),('QA held-out90',held)]:lines.append('- '+label+'：'+(compact(data['worker_failures']['any_worker_failed_or_timeout'])+'；RAG '+compact(data['worker_failures']['rag_failed_or_timeout'])+'；DB '+compact(data['worker_failures']['database_failed_or_timeout']) if data else '未执行'))
    lines.append('')
    lines += ['**Chap12工程门禁覆盖范围**（QA整体failed+timeout，历史，非Worker口径）：'+ '；'.join(name+' '+compact(data['overall_failed_or_timeout']) for name,data in oldworker.items() if 'QA' in name),'', '| 三类对照 | 结果 |','| --- | --- |', '| 原RAG / Agentic | 本轮未新增；既有历史证据保留 |', '| 单Agent / 固定Workflow / 新版本 | '+ ('前两者各不支持150/150（接口契约核验，未执行组合调用）；新版本完整率'+compact(business['metrics']['complete'])+'；未完整/计数差异'+str(len(business['regression_items']))+'题次，不预设优势' if business else '本轮未执行；原版本缺独立统计能力')+' |','| 可靠性改动前 / 后 | 未执行 |','', '| QA R@5 / R@10 / MRR（同分区三重复） | v0 | 当前90秒 |','| --- | --- | --- |']
    for p,c in comparison.items():
        fmt=lambda m:' / '.join(compact(m[k]) for k in ('recall_at_5','recall_at_10','mrr')) if m else '未执行'
        lines.append('| '+p+' | '+fmt(c['v0'])+' | '+fmt(c['current'])+' |')
    lines += ['',f"**已知限制**：S14未通过；原成功对照历史退化{oldquality['control_regressed_questions']}题/{oldquality['control_regressed_question_repeats']}题次。初轮归因{report['regression_attribution']}；剩余归因{diagnosis2['primary_attribution_distribution']}。completed不等于事实正确。",f"历史N拒答{n['numerator']}/{n['denominator']}，95%CI{[round(v,3) for v in n['cluster_bootstrap95']]}；均值{n['mean']:.3f}、范围{[round(v,3) for v in n['range']]}；冻结v0结论不变。",'**评分状态**：待盲评；旧LLM评分作废，未引用一致率；旧盲评包弃用。'+(f"新包{export['nonempty_answer_groups']}份，空/失败自动0为{export['auto_zero_observations']}题次并排除一致率。" if export else '最终确认性运行尚未完成，未导出新包。'),'', '| 状态分布/所用预算 | completed | partial | no_data | permission_denied | timeout | failed | 合计 |','| --- | --- | --- | --- | --- | --- | --- | --- |']
    if tune:lines.insert(lines.index('**评分状态**：待盲评；旧LLM评分作废，未引用一致率；旧盲评包弃用。'+(f"新包{export['nonempty_answer_groups']}份，空/失败自动0为{export['auto_zero_observations']}题次并排除一致率。" if export else '最终确认性运行尚未完成，未导出新包。')),f"当前控制集退化{tune['control_regressed_questions']}题/{tune['control_regressed_question_repeats']}题次（检索/正文F1辅助指标，仅tune/对照；事实覆盖待盲评）。")
    for label,x in states.items():lines.append('| '+label+' | '+' | '.join(str(x['counts'][s]) for s in STATES)+f" | {sum(x['counts'].values())}/{x['denominator']} |")
    batches=read(root/'evals/project2-v1/calibration_v031/batches.json')['batches']
    lines+=['','**标定批次**：'+'；'.join(f"批次{x['batch']} {x['status']}、{x['requests']}条、用于决策={x['used_for_decision']}、删失原因={x['censor_reason']}" for x in batches)+'。', '**规格修订**：'+'；'.join(x['version']+' '+str(x['delta_count'])+'处' for x in revisions)+'。v0.3.3仅恢复90秒下限/启动预热；累计执行、不计停机，依赖/LLM阈值未变。',f"**两表一致性**：{consistent['status']}，批准/运行各{consistent['approved_rows']}行；文档{len(checks)}行PASS，v0的{len(baseline['sut']['files'])}个文件哈希未变。",'', '本人待办：新包做盲评；处理Docker本地socket启动故障后再续Chap14；最终审阅、git push/PR另行处理；第16章云账号与预算另行授权；向老师确认CL-03（Fake Publish未做）。', f"[机器证据/CI](<{(audit/'summary.json').as_posix()}>) · [只读诊断](<{(audit/'budget_diagnosis.json').as_posix()}>) · [续跑记录](<{(root/'specs/project2/progress.md').as_posix()}>)。"]
    if feasibility:
        lines.append(f"容器前置：全量{feasibility['full_chunks']} Chunk，索引{feasibility['asset_bytes']['.rag_data/techqa_semantic']/2**30:.2f}GiB，全文库{feasibility['asset_bytes']['.rag_data/techqa_full.sqlite']/2**30:.2f}GiB；[本地启动诊断](<{(root/'specs/project2/container_startup_diagnosis.md').as_posix()}>)。真实容器门禁未执行。")
    if checkpoint:
        lines.append(f"本地提交 `{checkpoint['commit'][:12]}`；提交文件校验{checkpoint['committed_bytes']['matched']}/{checkpoint['committed_bytes']['checked']}。未push/PR；停止诊断及最终派生汇总在提交后保留。")
    if export:lines.append(f"[新盲评包](<{(root/export['public_markdown']).as_posix()}>)；key另存，评分前勿查看。")
    discrepancy=report['count_discrepancy']
    if discrepancy:
        lines.insert(next(i for i,line in enumerate(lines) if line.startswith('**评分状态**')),
            f"组合谓词/澄清冲突{discrepancy['discrepant_tasks']}任务/{discrepancy['discrepant_observations']}题次；计数比对保留{discrepancy['count_exact_numerator']}/{discrepancy['requests']}，含URL内版本误绑定。未改冻结预期、源码或门禁，不称核心计数全部验收。")
    for index,line in enumerate(lines):
        if line.startswith('停止原因：'):lines[index]='停止原因：'+(reason or '无；流程执行中').rstrip('。')+'。'
        if line.startswith('| 原RAG / Agentic |'):
            value=report['comparisons'][0]['summary']
            if value is None:lines[index]='| 原RAG / Agentic | 未执行；没有实测对照结论 |'
        elif line.startswith('| 单Agent / 固定Workflow / 新版本 |') and business:
            unsupported='；'.join(f"{name}不支持{data['unsupported_numerator']}/{data['task_denominator']}" for name,data in business['legacy'].items())
            lines[index]='| 单Agent / 固定Workflow / 新版本 | '+unsupported+'（接口契约核验，未执行组合调用）；新版本完整率'+compact(business['metrics']['complete'])+'；计数一致'+compact(business['metrics']['count_exact'])+'；未完整/计数差异'+str(len(business['regression_items']))+'题次，不预设优势 |'
    # Keep every value/link while respecting the existing one-page contract.
    # These are adjacent prose paragraphs, not table rows or evidence removal.
    for prefix in ('**规格修订**','**两表一致性**','容器前置：','本地提交 `','[新盲评包]'):
        index=next((i for i,line in enumerate(lines) if line.startswith(prefix)),None)
        if index is not None and index>0 and lines[index-1]:
            lines[index-1]+=' '+lines.pop(index)
    assert len(lines)<=55
    markdown='\n'.join(lines)+'\n'
    save(audit/'execution_state.json',state);save(audit/'summary.json',report)
    atomic_text(root/'specs/project2/summary.md',markdown)
    atomic_text(root/'specs/project2/progress.md','# Project 2 自动执行续跑记录\n\n'+json.dumps(state,ensure_ascii=False,indent=2)+'\n\n已通过/失败门禁见audit/project2-v1/summary.json。旧37.941秒结果保留，新90秒记录独立；S14未通过，不记Chap12完整通过。续跑先读本文件。held-out按已登记阶段一次，无重新选题。评分暂停，旧盲评包弃用，新包仅最终代码与确认性运行完成后导出。Chap16/远端/付费/安装/Fake Publish均不在范围。\n')
    return markdown
