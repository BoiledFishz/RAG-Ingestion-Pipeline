"""Only the directly authorized cumulative-execution-time specification delta."""
from __future__ import annotations
import csv
import hashlib
import json
import shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
AUTH='''【用户授权（本人决定，日期 2026-10-06，原文如下）】
授权你创建 specs/project2/v0.3.2，仅限第 1 项修订；第 2 至 7 项为授权内的执行。
其余一律不得改动，包括预算数值（19 次依赖、6 次 LLM、37.941 秒）、S07、S14、门禁、held-out 规则、CL 决定。
超出范围的改动停止并报告。把本授权原文与日期追加到批准附录，已批准文件保持不变。

1. 恢复期限记账：期限改为"累计执行时间"，跨执行片段求和，不含停机时间，数值不变；
   依赖与 LLM 尝试计数持久化并跨恢复累计，恢复不得清零；
   新增运行存活上限 15 分钟（暂定值，开跑前写入并记哈希），超过则 timeout 或 failed，不静默新建运行；
   AC13-02 保持：累计超限或存活上限过期必须失败，不得重置预算。
2. 先列出 Chap13 门禁两项失败的全部检查名称与原因（摘要只说了一项），并实测重启耗时（进程启动、索引加载），写入证据文件。
3. 修订后重新计门禁，最多修复两轮，仍不过则停止；不为随机性重复门禁。
4. 退化第二轮（授权内剩余一轮）：先对剩余 9 题逐题归因；对组合路径 6 个 failed、QA 路径剩余 6 个 failed 和 3 个 timeout、
   以及 41 个 partial 的成因分类（若 partial 仅因 DB no_data，说明其不是质量退化，但不改 S07 与 CL-01）。
   只修 Project 2 自己的代码缺陷；根因是冻结预算或 v0 行为的，写入已知限制。
   修复数字标注"仅 tune/对照集"。另查明上次"退出清理失败"的原因，只修清理逻辑，不重跑已完成记录。
5. held-out：Chap13 阶段末运行一次，这是修复后系统的第一次确认性运行，累计第 2 次，在汇总中披露。
   运行前先在 tune 上做冒烟：failed 加 timeout 的比例超过 10% 就停止，不消耗 held-out。结果不佳只如实报告，不得调参。
6. 评分：暂停 LLM 评分。把旧评分文件标注"作废：空正文、全同分、基于修复前答案"，不得在汇总中作为一致率引用。
   代码定稿后导出盲评包：打乱顺序，去掉系统、版本、分区和已有评分，key.json 另存；
   只含非空答案，空或失败答案按规则记 0，不进入一致率；不得使用 3B 模型。导出后告诉我，由我做盲评。
7. 通过后继续 Chap14、Chap15，规则同前；不做第 16 章、不 push、不建 PR、不使用付费资源。

汇总新增：
- 「Chap12 工程门禁覆盖范围」：QA 路径 (failed+timeout)/总数，修复前后各一行；
- 评分状态节改为"待盲评"；
- 恢复期限记账的修订写入"规格修订"，并写明阈值未变。'''

ADDITION='''### S08.3 v0.3.2 恢复期限累计执行记账（2026-10-06 实现前授权）

本段仅替代恢复时的期限记账语义；已冻结数值为19次依赖、6次LLM、37.941018秒（摘要显示37.941秒），数值、标定原记录/公式/熔断不变。请求执行片段从默认API预算建立到响应/中断清理结束，按单调时钟累计；恢复的新片段只获得原执行总额减去已消费时间的余额，不把整额重置。停止服务、重新启动进程与依赖就绪/全量索引加载但尚未恢复该请求的时间不计执行消费。片段内等待模型、SQL、重试、元数据持久化、渲染和取消仍计入。

消费量在尝试预留、节点结果及结束/中断时持久化，执行中以0.25秒周期保存时间心跳。非正常终止未确认的最后一个周期保守计入消费，不将它算作0；正常关闭保存实际结束时间。记录每个片段及其消费，跨恢复求和；依赖/LLM累计计数和结果不清零。瞬时绝对截止是余额在当前片段的执行边界，不能再被误当成跨停机不变的截止时间。

新增运行存活上限900秒（15分钟暂定值），从首次运行created_at算起，含停机；该值在任何v0.3.2真实门禁前登记并记录SHA256。它与State保留24小时、Trace保留7天不同，不改变CL决定。累计执行超限或存活超限时明确timeout或failed；不静默新建运行，不清零计数。原AC13-02的拒绝门禁保持，改为检查累计超限/存活超限及原损坏/版本/权限边界。

其余S07/S14、场景集合/原查询、门禁成功条件、授权/非目标、CL决定及held-out冻结协议不变。第13章确认性held-out调用与tune冒烟、旧评分作废及盲评导出是本次执行授权，记录在批准附录及执行账本，不改评测协议。

'''

def sha(path: Path) -> str:return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path: Path,value) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def build() -> None:
    old=ROOT/'specs/project2/v0.3.1';new=ROOT/'specs/project2/v0.3.2'
    if new.exists():raise ValueError('New version already registered; never overwrite approved records')
    protected={p.relative_to(ROOT).as_posix():sha(p) for version in ('v0.1','v0.2','v0.3','v0.3.1')
               for p in (ROOT/'specs/project2'/version).iterdir() if p.is_file()}
    new.mkdir()
    for p in old.iterdir():
        if p.is_file() and p.name not in {'check_docs.py','delta.md','delta.json','approval_addendum.md','version_manifest.json'}:
            shutil.copyfile(p,new/p.name)
    anchor='<a id="s09"></a>';original=(old/'spec.md').read_text(encoding='utf-8')
    if original.count(anchor)!=1:raise ValueError('Ambiguous insertion anchor')
    (new/'spec.md').write_text(original.replace(anchor,ADDITION+anchor),encoding='utf-8')
    rows=list(csv.DictReader((old/'acceptance_scenarios.csv').open(encoding='utf-8-sig',newline='')))
    changes=[{'file':'spec.md','category':'recovery_time_accounting_only','old':anchor,'new':ADDITION+anchor}]
    edits={('AC13-01','setup'):'合法请求中间结果、尝试及累计执行时间已持久化；执行余额为正且未到900秒存活上限',
           ('AC13-02','setup'):'隔离Runtime副本的累计执行时间已超限，或900秒存活上限已过期；重新验权合法但不得恢复调用。损坏/版本错误另用明确failed/failed→failed子案例，不与本行超时期望混写。',
           ('AC13-02','assertions'):'S07[rag=timeout,db=timeout]=timeout；未知/非法显式失败；累计超限或900秒存活过期不能重置预算；不静默创建新运行'}
    for row in rows:
        for (sid,key),value in edits.items():
            if row['scenario_id']==sid:
                changes.append({'file':'acceptance_scenarios.csv','scenario_id':sid,'column':key,'old':row[key],'new':value,'category':'recovery_time_accounting_only'})
                row[key]=value
    with (new/'acceptance_scenarios.csv').open('w',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]),quoting=csv.QUOTE_ALL,lineterminator='\r\n');writer.writeheader();writer.writerows(rows)
    policy={'version':'project2-cumulative-execution-v032','authorization_date':'2026-10-06',
            'dependency_limit':19,'llm_limit':6,'execution_limit_seconds':37.941018,'run_lifetime_seconds':900,
            'run_lifetime_status':'暂定，已在运行前登记','heartbeat_seconds':.25,
            'uncertain_tail':'conservatively charge one heartbeat interval, never reset consumption',
            'state_retention_seconds':86400,'trace_retention_seconds':604800,
            'heldout_confirmatory_stage_calls':1,'smoke_failure_fraction_max':.10,'llm_judging':'paused',
            'old_budget_file':'evals/project2-v1/calibration_v031/budget_frozen.json',
            'old_budget_sha256':sha(ROOT/'evals/project2-v1/calibration_v031/budget_frozen.json')}
    save(new/'recovery_accounting.json',policy)
    save(new/'delta.json',{'from_version':'v0.3.1','to_version':'v0.3.2','authorization_date':'2026-10-06',
                         'changes':changes,'protected_files':protected,'limits_changed':False})
    (new/'delta.md').write_text('# v0.3.1 → v0.3.2\n\n2026-10-06用户在实现之前授权，仅恢复期限记账：累计执行片段、不计停机；新增900秒存活上限。\n\n'+
         '\n'.join('- '+json.dumps(x,ensure_ascii=False) for x in changes)+'\n\n原19/6/37.941018阈值、S07、S14、门禁成功条件及其他CL决定不变。旧版本逐文件哈希见delta.json。\n',encoding='utf-8')
    appendix=ROOT/'specs/project2/approval_appendix_2026-10-06_v032.md'
    if appendix.exists():raise ValueError('Authorization appendix already exists')
    appendix.write_text('# v0.3.2 直接用户授权\n\n本人决定日期：2026-10-06；授权发生在本次实现之前。未代填人工审阅栏。\n\n'+AUTH+'\n',encoding='utf-8')
    shutil.copyfile(appendix,new/'approval_addendum.md')
    save(ROOT/'audit/project2-v1/v032_authorization.json',{'origin':'direct_user_message','authorization_file':appendix.relative_to(ROOT).as_posix(),
         'sha256':sha(appendix),'spec_version':'v0.3.2','limits_changed':False,'s14_waived':False,'llm_judging':'paused'})

if __name__=='__main__':build()
