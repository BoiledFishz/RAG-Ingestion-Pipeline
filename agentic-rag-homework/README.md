# TechQA Agentic RAG 与 Multi-Agent 实验

RAG、Search、Document Retrieval 三个 Tool 均读取官方 IBM TechQA。默认共用根项目的全量 MiniLM/Faiss 语义 Dense、
SQLite BM25 和有限候选 nomic 重排；原 AWS 合成知识库和外部搜索语料已移除。
Search 是同一官方文档库的 BM25 检索，不表示联网搜索。Document Tool 按原始 IBM 文档 ID 读取原文。

## 运行

先按根 README 准备全量索引及本地 Ollama。从本目录：

```powershell
python -m pip install -e "..[dev,api]"
python -m pytest
python -m uvicorn api.main:app --host 127.0.0.1 --port 8002
python -m evaluation.run --provider ollama --planner-runs 10 --output evaluation/results/techqa_semantic
python -m evaluation.critic_stability --limit 5 --repeats 2 --output evaluation/results/techqa_semantic_critic
python -m evaluation.critic_stability --evidence-mode retrieved --split fixture --label all --limit 15 --repeats 2 --output evaluation/results/techqa_semantic_critic_retrieved
```

默认 `MODEL_PROVIDER=ollama`。`demo` 仅是单元测试的结构化模型替身，不是实际 LLM Planner 成绩。
单元测试设置 `TECHQA_PROFILE=fixture`，使用提交的 41 篇官方文档；服务与实验默认 full。

## 作业对应

| 功能 | 实现与验收 |
|---|---|
| Rewrite / Retriever / Compression | `agents/rag_agent`，原始 TechNote 相关段落、解决步骤、来源 ID |
| Structured Output | answer/sources/confidence，缺来源 confidence=0 |
| LLM Planner | JSON Schema、Agent 枚举、顺序 ID、DAG；每条最终路径必须经过 Diagnosis/Critic |
| ReAct | 首次 RAG 后模型决定继续 search/read_document 或 finish；动作重复/非法 ID 有界恢复 |
| Critic Loop | 问题记录、Feedback 回灌、最多两次 Retry；未通过则停止发布答案 |
| Single / Multi | 同一数据和工具；保存调用数、估算 Token、延迟、正文质量与失败率 |

接口：`POST /v1/rag/query`、`/v1/planner`、`/v1/research`、`/v1/critic-loop`、
`/v1/single-agent`、`/v1/multi-agent`，以及 `GET /healthz`。

证据选择器只返回 `sufficient` 和原文段落 ID；正文由程序渲染所选原文，减少无关长文和虚构事实。
ReAct 的最终证据校验失败时，在动作预算内再做一次 Sparse 核验；单条轨迹最多 5 个动作。
模型不可用会单独报告并记入 `model_errors`，不冒充知识库无答案的成功拒答。
生产 Diagnosis 只选择原文证据 ID；Critic 独立验证所选原文是否充分回答问题。
复核只读取所引用的文档上下文；验证拒答时分批检查全部候选，不能要求编造缺失事实。
只有后续复核真正通过，才记录上一轮问题已解决；复核通过与给出充分答案分别统计。
Critic 最终失败时返回“复核未通过”，sources=[]、confidence=0；错误会传递至最终报告，
不能回退发布先前已被否决的答案，也不计为知识库拒答成功。
分析和报告节点保留依赖节点的已验证回答，避免交接时丢失答案或重新附加无关正文。

示例问题直接取官方 `TRAIN_Q000`：升级 Streams 4.1.1.1/4.1.1.2 后 .bashrc 环境变量未生效。
可直接使用该题原始标题请求：`{ "query": "User environment variables no longer getting picked up after upgrade to 4.1.1.1 or 4.1.1.2?" }`。
完整真实请求/响应见父目录 `evals/techqa_semantic_api_smoke.json`。

## 实验与限制

[报告](evaluation/results/techqa_semantic/report.md) 和 [原始轨迹](evaluation/results/techqa_semantic/runs.json)
使用 15 条官方训练题，检索范围是全库。多 Agent 的 Research、Diagnosis 和 Critic 调用真实 LLM；
Data Analyst 与 Report Writer 是确定性证据处理器。跨 Agent 只能读取显式依赖节点的输出。
`techqa` 保存旧模型的历史实验。Critic 重复实验分别记录参考证据与实际检索证据，
报告通过率、回答接受率、正文 F1、拒答比例及重复运行的一致性；高通过率不能替代答案质量。
开发期间的真实失败记录保存在 `evaluation/results/techqa_critic_development`。

答案质量是正文与官方参考答案的 Token F1，并要求引用正确文档；sources 字段和引用编号不参与得分。
正文中的逐字证据仍是实际回答。另列有答案题的正文 F1 与 N 标签拒答比例，避免把两者混在一起。
这是一项可复现代理指标，不能判断所有语义等价改写。报告的 Failure Rate 采用严格“质量未满分或执行异常”
定义，不能等同于运行崩溃率。异常计零且保留在分母。Token 数是正则估算，非供应商计费数。
官方 N 标签仅保证候选 DOC_IDS 内无答案，全库查询可能发现其他证据；模糊问题检查使用最短的官方问题标题，
保留原文但暂不提供详细正文，不编造问题。没有检索证据的 Critic 试验记录 `run=null`，
不调用模型，不计复核通过；仍保留在答案质量分母。

Multi-Agent 不一定优于 Single Agent。更多规划和复核增加了调用、延迟及出错机会，必须用实际质量收益衡量。

本轮真实模型四版本共 60 次执行，执行错误为 0；Planner 10 次均满足 Schema 和执行路径校验。
但 Single/Multi 有答案题正文 F1 仅为 0.189/0.153；Multi 的官方 N 标签拒答比例为 0.333。
实际检索后的 Critic 重复 30 次，充分性和诊断一致率均为 1.00，但有答案题接受率只有 0.50。
这些结果说明流程和复核稳定性有改进，仍不满足生产问答质量要求，不能仅用 Critic 通过率签收。
上述 `techqa_semantic` 数字为整改前已归档结果。本轮共享压缩器保留完整指令组，并检查安装/回滚、
明确 Socket 组件和同一产品最低版本错误的冲突；Critic 针对这些冲突给出来源 ID 与替换建议。
父目录 `./scripts/run-remediation-checks.ps1` 使用真实 TechQA 全量检索和新结果目录复验，
不会把历史 60 次运行或旧 Critic 结果冒充当前代码的成绩。
[本轮 60 次比较](evaluation/results/techqa_remediation_v4/report.md) 执行异常为 0，
Single/Multi 的 Y 正文 F1 是 0.2439/0.2081，仍不足以签收。
[本轮 30 次 Critic](evaluation/results/techqa_remediation_v4_critic/summary.json) 一致性为 1.00，
但 Y 接受率仍为 0.50、Y 正文 F1 回落至 0.1406。完整结果与范围限制见父目录整改报告。
`python -m mypy` 与 `python -m ruff check .` 分别检查类型与代码规范；三项目测试用父目录 `scripts/test_all.py`。
