# TechQA Agentic RAG 与 Multi-Agent 实验

RAG、Search、Document Retrieval 三个 Tool 均读取官方 IBM TechQA。默认共用根项目的全量 Qdrant、
SQLite BM25 和有限候选 nomic 重排；原 AWS 合成知识库和外部搜索语料已移除。
Search 是同一官方文档库的 BM25 检索，不表示联网搜索。Document Tool 按原始 IBM 文档 ID 读取原文。

## 运行

先按根 README 准备全量索引及本地 Ollama。从本目录：

```powershell
python -m pip install -e "..[dev,api]"
python -m pytest
python -m uvicorn api.main:app --host 127.0.0.1 --port 8002
python -m evaluation.run --provider ollama --planner-runs 10 --output evaluation/results/techqa
```

默认 `MODEL_PROVIDER=ollama`。`demo` 仅是单元测试的结构化模型替身，不是实际 LLM Planner 成绩。
单元测试设置 `TECHQA_PROFILE=fixture`，使用提交的 41 篇官方文档；服务与实验默认 full。

## 作业对应

| 功能 | 实现与验收 |
|---|---|
| Rewrite / Retriever / Compression | `agents/rag_agent`，原始 TechNote 相关段落、解决步骤、来源 ID |
| Structured Output | answer/sources/confidence，缺来源 confidence=0 |
| LLM Planner | JSON Schema、允许的 Agent 枚举、顺序 ID、DAG 校验；真实计划驱动执行 |
| ReAct | 首次 RAG 后模型决定继续 search/read_document 或 finish；动作重复/非法 ID 有界恢复 |
| Critic Loop | 问题记录、Feedback 回灌、最多两次 Retry；未通过时明确标记降级 |
| Single / Multi | 同一数据和工具；保存调用数、估算 Token、延迟、正文质量与失败率 |

接口：`POST /v1/rag/query`、`/v1/planner`、`/v1/research`、`/v1/critic-loop`、
`/v1/single-agent`、`/v1/multi-agent`，以及 `GET /healthz`。

示例问题直接取官方 `TRAIN_Q000`：升级 Streams 4.1.1.1/4.1.1.2 后 .bashrc 环境变量未生效。
请求 `{ "query": "How are Streams environment variables set after upgrade to 4.1.1.2?" }`。
完整真实请求/响应见父目录 `evals/techqa_api_smoke.json`。

## 实验与限制

[报告](evaluation/results/techqa/report.md) 和 [原始轨迹](evaluation/results/techqa/runs.json)
使用 15 条官方训练题，检索范围是全库。多 Agent 的 Research、Diagnosis 和 Critic 调用真实 LLM；
Data Analyst 与 Report Writer 是确定性证据处理器。跨 Agent 只能读取显式依赖节点的输出。

答案质量是正文与官方参考答案的 Token F1，并要求引用正确文档；来源引文和引用编号不参与正文得分。
这是一项可复现代理指标，不能判断所有语义等价改写。报告的 Failure Rate 采用严格“质量未满分或执行异常”
定义，不能等同于运行崩溃率。异常计零且保留在分母。Token 数是正则估算，非供应商计费数。
官方 N 标签仅保证候选 DOC_IDS 内无答案，全库查询可能发现其他证据；模糊输入 `help` 是接口行为控制项，
不是新增的知识库语料或黄金答案。

Multi-Agent 不一定优于 Single Agent。更多规划和复核增加了调用、延迟及出错机会，必须用实际质量收益衡量。
