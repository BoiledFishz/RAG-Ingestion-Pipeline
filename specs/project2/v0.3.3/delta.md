# v0.3.2 → v0.3.3

2026-10-06 实现前直接授权。

- {"file": "spec.md", "old": "<a id=\"s09\"></a>", "new": "### S08.4 v0.3.3 签署墙钟下限与启动语义（2026-10-06 实现前授权）\n\n本段仅替代此前37.941018秒的执行上限与未明确的预热边界：最终累计执行上限=max(最初签署90秒,原v0.3公式37.941018秒)=90秒。依赖19、LLM6、累计执行记账、900秒存活上限、持久化计数、S07、S14、门禁与CL决定不变。批次2原测量与选择结果不改写；所有历史37.941018秒结果独立保留，标注“预算37.941秒”，不得混合平均。标定观测包本身使用300秒离线观测包络，不能误标为37.941秒请求。\n\n索引与嵌入模型在每个服务Worker进程启动时一次性加载并执行真实预热；就绪只能在加载及预热成功后通过，失败则不就绪。预热只使用官方全文库按确定性顺序读取的文档正文，不使用QA目标、答案或标签，不调用生成LLM，不生成语料。预热记录输入文本哈希、加载/嵌入推理/索引预热耗时和完成状态。服务启动或故障后重启的加载、预热发生在接受运行之前，不消费任何运行的期限、依赖或LLM余额；运行内排队、Worker执行、模型等待、持久化、清理仍计时。请求期间发现Worker不就绪时明确失败，不在已建立运行内偷偷冷加载。服务自动重启使用有界启动期限（原180秒），期间健康检查ready=false；不得绕过授权、运行预算或默默重建run_id。\n\n本次Worker级别tune冒烟与阶段末一次held-out、旧盲评包弃用是直接执行授权，单独登记于执行协议，不修改冻结S14或held-out协议。90秒推算不作为通过证据，必须重新运行原工程检查。\n\n<a id=\"s09\"></a>", "category": "authorized_wall_floor_and_startup"}
- {"file": "recovery_accounting.json", "field": "execution_limit_seconds", "old": 37.941018, "new": 90, "category": "signed_floor"}
- {"file": "recovery_accounting.json", "field": "version", "old": "project2-cumulative-execution-v032", "new": "project2-cumulative-execution-v033", "category": "versioned_policy"}

只读诊断：audit/project2-v1/budget_diagnosis.json。same_run_id要求整体completed；ID实际未丢，RAG因37.941018秒累计执行耗尽而timeout，答案为空使unchanged_native_answer_body失败。依赖15/19、LLM4/6，未触发计数上限；24.928936秒重启加载在v0.3.2已排除。90秒是否足够尚未执行，不能保证后续被删失的LLM调用完成。启动预热另按S08.4执行。

所有场景、S07、S14、CL与计数上限原样保留。
