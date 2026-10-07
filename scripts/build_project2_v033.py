"""Register only the user's 90s floor and startup warmup specification delta."""
from __future__ import annotations
import json
import shutil
from pathlib import Path
from build_project2_v032 import sha,save
ROOT=Path(__file__).resolve().parents[1]
AUTH='''【用户授权（本人决定，日期 2026-10-06，原文如下）】
授权创建 specs/project2/v0.3.3，仅限第 1、2 项修订；第 3 至 8 项为授权内执行。
其余一律不得改动：依赖上限 19、LLM 上限 6、S07、S14、门禁定义、held-out 规则、CL 决定。
超出范围停止并报告。本授权原文与日期追加到批准附录，已批准文件保持不变。

1. 墙钟上限恢复为我最初签署的 90 秒：最终值 = max(已签署 90 秒, v0.3 公式值)，与此前对依赖和 LLM 上限的"只升不降"一致。
   此前在 37.941 秒下得到的全部结果保留并标注"预算 37.941 秒"，不得与新预算下的结果混合或平均。
2. 启动语义：索引与嵌入模型在启动时一次性加载并预热，预热不计入任何运行的预算；就绪检查在加载与预热完成后才通过。

3. 先做只读诊断，不新增运行，写入 audit/project2-v1/budget_diagnosis.json：
   a. Chap13 门禁时间线：重启前后每个节点的执行耗时、重启后冷启动各环节是否被计入期限；
      逐条写明 same_run_id 与 unchanged_native_answer_body 两项检查的判定逻辑和失败原因；不得修改门禁定义；
      并推算：在 90 秒与预热完成的前提下该场景是否仍会超时。
   b. QA 路径：33 个 RAG 超时的请求特征；已完成请求的 RAG 耗时分布，与标定批次 2 的 RAG 单独耗时对比
      （按重复序号、进程启动后的首次请求分别统计），说明标定负载是否更轻或更热。
   c. 评测期间是否有并发请求或其他进程占用同一模型服务。

4. 冒烟标准改为 Worker 级别：任一 Worker 状态为 timeout 或 failed 的请求占比，在 tune 冒烟上不超过 10%。
   取代此前"整体 failed+timeout"的口径，因为 RAG 超时在整体状态上显示为 partial。

5. 按新上限重跑 Chap12 工程门禁中与墙钟相关的故障注入测试（如 AC12-05、AC12-16），更新追踪证据。
   然后重跑 Chap13 门禁，给 2 轮新的修复额度；仍不过就停止，不为随机性重复门禁。

6. 门禁通过后，先做 tune 冒烟（第 4 项标准）：
   - 达标：运行 held-out 一次，这是修复后系统的第一次确认性运行，累计第 2 次，汇总中披露，结果不佳只如实报告，不得调参；
   - 不达标：不消耗 held-out，停止并报告 Worker 级别失败的归因。

7. 评分：不使用修复前的历史盲评包。待最终代码与确认性运行完成后导出新的盲评包
   （打乱顺序，去掉系统、版本、分区和已有评分，key 另存，空或失败答案按规则记 0 并排除一致率），导出后告诉我，由我评。

8. 通过后继续 Chap14、15，规则同前；不做第 16 章、不 push、不建 PR、不使用付费资源。

汇总新增：
- 「预算历史」：90（签署初始）→ 37.941（标定，对应哪些结果）→ 90（v0.3.3 恢复），逐项标明各结果所用预算；
- QA 与组合路径各自的 Worker 级别 timeout/failed 比例；
- 其余各节保持。'''
ADDITION='''### S08.4 v0.3.3 签署墙钟下限与启动语义（2026-10-06 实现前授权）

本段仅替代此前37.941018秒的执行上限与未明确的预热边界：最终累计执行上限=max(最初签署90秒,原v0.3公式37.941018秒)=90秒。依赖19、LLM6、累计执行记账、900秒存活上限、持久化计数、S07、S14、门禁与CL决定不变。批次2原测量与选择结果不改写；所有历史37.941018秒结果独立保留，标注“预算37.941秒”，不得混合平均。标定观测包本身使用300秒离线观测包络，不能误标为37.941秒请求。

索引与嵌入模型在每个服务Worker进程启动时一次性加载并执行真实预热；就绪只能在加载及预热成功后通过，失败则不就绪。预热只使用官方全文库按确定性顺序读取的文档正文，不使用QA目标、答案或标签，不调用生成LLM，不生成语料。预热记录输入文本哈希、加载/嵌入推理/索引预热耗时和完成状态。服务启动或故障后重启的加载、预热发生在接受运行之前，不消费任何运行的期限、依赖或LLM余额；运行内排队、Worker执行、模型等待、持久化、清理仍计时。请求期间发现Worker不就绪时明确失败，不在已建立运行内偷偷冷加载。服务自动重启使用有界启动期限（原180秒），期间健康检查ready=false；不得绕过授权、运行预算或默默重建run_id。

本次Worker级别tune冒烟与阶段末一次held-out、旧盲评包弃用是直接执行授权，单独登记于执行协议，不修改冻结S14或held-out协议。90秒推算不作为通过证据，必须重新运行原工程检查。

'''
def build():
    old=ROOT/'specs/project2/v0.3.2';new=ROOT/'specs/project2/v0.3.3'
    if new.exists():raise ValueError('Already registered; never overwrite approved files')
    if not (ROOT/'audit/project2-v1/budget_diagnosis.json').is_file():raise ValueError('Read-only diagnosis must precede revision')
    protected={p.relative_to(ROOT).as_posix():sha(p) for version in ('v0.1','v0.2','v0.3','v0.3.1','v0.3.2') for p in (ROOT/'specs/project2'/version).iterdir() if p.is_file()}
    new.mkdir()
    for p in old.iterdir():
        if p.is_file() and p.name not in {'check_docs.py','delta.md','delta.json','approval_addendum.md','version_manifest.json'}:shutil.copyfile(p,new/p.name)
    original=(old/'spec.md').read_text(encoding='utf-8');anchor='<a id="s09"></a>'
    assert original.count(anchor)==1
    (new/'spec.md').write_text(original.replace(anchor,ADDITION+anchor),encoding='utf-8')
    before=json.loads((old/'recovery_accounting.json').read_text(encoding='utf-8'));after={**before,'version':'project2-cumulative-execution-v033','execution_limit_seconds':90}
    save(new/'recovery_accounting.json',after)
    changes=[{'file':'spec.md','old':anchor,'new':ADDITION+anchor,'category':'authorized_wall_floor_and_startup'},
             {'file':'recovery_accounting.json','field':'execution_limit_seconds','old':before['execution_limit_seconds'],'new':90,'category':'signed_floor'},
             {'file':'recovery_accounting.json','field':'version','old':before['version'],'new':after['version'],'category':'versioned_policy'}]
    save(new/'delta.json',{'from_version':'v0.3.2','to_version':'v0.3.3','changes':changes,'protected_files':protected,
        'diagnosis_file':'audit/project2-v1/budget_diagnosis.json','diagnosis_sha256':sha(ROOT/'audit/project2-v1/budget_diagnosis.json')})
    (new/'delta.md').write_text('# v0.3.2 → v0.3.3\n\n2026-10-06 实现前直接授权。\n\n'+
        '\n'.join('- '+json.dumps(x,ensure_ascii=False) for x in changes)+
        '\n\n只读诊断：audit/project2-v1/budget_diagnosis.json。same_run_id要求整体completed；ID实际未丢，RAG因37.941018秒累计执行耗尽而timeout，答案为空使unchanged_native_answer_body失败。依赖15/19、LLM4/6，未触发计数上限；24.928936秒重启加载在v0.3.2已排除。90秒是否足够尚未执行，不能保证后续被删失的LLM调用完成。启动预热另按S08.4执行。\n\n所有场景、S07、S14、CL与计数上限原样保留。\n',encoding='utf-8')
    appendix=ROOT/'specs/project2/approval_appendix_2026-10-06_v033.md'
    if appendix.exists():raise ValueError('Approval appendices append-only')
    appendix.write_text('# v0.3.3 直接用户授权\n\n本人决定日期：2026-10-06；实现前授权，不代填人工审阅栏。\n\n'+AUTH+'\n',encoding='utf-8')
    shutil.copyfile(appendix,new/'approval_addendum.md')
    save(ROOT/'audit/project2-v1/v033_authorization.json',{'authorization_file':appendix.relative_to(ROOT).as_posix(),'sha256':sha(appendix),
        'spec_version':'v0.3.3','origin':'direct_user_message','s14_waived':False,'llm_judging':'paused'})
if __name__=='__main__':build()
