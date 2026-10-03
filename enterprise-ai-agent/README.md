# Enterprise TechQA Agent

这是同一仓库的 Agent Service。默认 Retriever 使用父项目 `rag.techqa` 共享全量检索：
固定版本 MiniLM 语义 Dense / Faiss + 全量 SQLite FTS5 BM25 + RRF + 有限候选 nomic 语义重排。
保留 Rewrite、Parent 获取、Context Compression、引用逐字验证与 answer/sources/confidence 输出。

## 获取全量官方数据

先按父目录 README 创建 Python 3.12 环境并安装 `.[dev,api,semantic]`。从父目录执行：

```powershell
./scripts/prepare-techqa.ps1
python scripts/verify_techqa_source.py
./scripts/start-local.ps1 -FullTechQA
```

准备脚本下载官方 GitHub 指向的 PrimeQA/TechQA tar.gz，校验固定 SHA-256 后安全解包。
断点重复执行会在 Embedding 前跳过已经存在的文本哈希。原始文件位于 `data/techqa/extracted/TechQA`，
已被 Git 忽略。全量源文件 801,998 条，2 条正文为空；实际全文索引 801,996 篇，详见父目录
`evals/techqa_source_inventory.json`。旧 Qdrant Hash 索引保留为显式基线；默认语义服务端口为 11435。

`training_dev_technotes.json` 有 28,482 篇；它不是全量库。当前默认 full 服务不把 core 成绩当全量成绩。

## 运行

```powershell
# 从 enterprise-ai-agent 目录
python -m pytest
$env:AGENT_RETRIEVAL_BACKEND = "techqa"
$env:AGENT_PROFILE = "ollama"
python -m uvicorn api.main:app --host 127.0.0.1 --port 8001
```

`AGENT_PROFILE=ollama` 使用真实 LLM Rewrite 和证据选择；`offline` 使用可复现规则改写/抽取，
数据始终为官方 TechQA，检索阶段 nomic 由共享 `TECHQA_RERANKER` 控制。
`AGENT_RETRIEVAL_BACKEND=legacy` 仅用于与旧 Hash 流程对比；其存储配置仍使用 `AGENT_*`。
共享服务配置由 `TECHQA_SEMANTIC_URL/TECHQA_INDEX_PATH` 决定；`TECHQA_DENSE_BACKEND=hash`
才使用 `TECHQA_QDRANT_URL/TECHQA_COLLECTION`。

API：`POST /v1/agent/query`，请求：

```json
{"query":"User environment variables no longer getting picked up after upgrade to 4.1.1.1 or 4.1.1.2?","filters":{"language":"en"}}
```

响应仅包含 `answer`、`sources`、`confidence`。无证据时 confidence=0。
最终 Top-k 之后取回 TechNote Parent，优先保留完整解决步骤及命令参数，避免只返回问题描述。
LLM 先判断证据是否直接回答问题，再选择来源 ID；程序按 ID 渲染经过验证的原文。
发布前另做一次独立适用性复核，只看拟发布的原文、标题与条件，拒绝错误产品、操作或症状条件。
隐藏在来源元数据中的条件不能当成答案已经说明的条件；复核失败则不发布。
程序核对冲突是否有原文依据，并忽略兼容版本、相同产品名称和不涉及相反方向的修复版本说明。
模型给出的“冲突”只是待验证判断；没有独立证明两个未知产品互斥时，不据此拒答。
无需模型复制长引文，避免截断或改写命令。无效结构或 ID 修复一次后仍错误则拒答。
默认最多 2400 Context Tokens、8 个来源；confidence 是证据覆盖启发值，不是校准过的事实正确率。

## 评测

```powershell
$env:AGENT_PROFILE = "ollama"
python -m evaluation.evaluate --output evaluation/results/techqa_semantic_v3
# 中断后以相同数据、代码和模型续跑；失败记录仍保留
python -m evaluation.evaluate --output evaluation/results/techqa_semantic_v3 --resume
# 对改进前 310 条实际结果隔离测试新增复核；不重复检索或改写
python -m evaluation.review_applicability --input evaluation/results/techqa_semantic/runs.json --output evaluation/results/new_review
# 三个服务和全部 Agent 端点的真实模型 HTTP 复验：从父目录执行
python scripts/smoke_techqa.py
```

[语义检索后的开发集结果](evaluation/results/techqa_semantic/summary.json) 对应增加独立适用性复核前的官方 310 题真实模型运行。
[原始逐题记录](evaluation/results/techqa_semantic/runs.json) 保留答案、引用、拒答、延迟和错误；异常记零并留在分母。
`techqa_shared` 是此前的离线规则实验，不是当前真实模型成绩。
`evaluation/results/full_hash_remediation` 是改进前真实全量 Hash 基线，不是当前默认流程。
新增复核的 [全开发集回放](evaluation/results/techqa_semantic_review/summary.json) 固定上述真实候选和初始答案，
只运行最终适用性复核。它不能冒充新版本的完整端到端评测；新版本完整复验应写到新的输出目录。
`techqa_semantic_review_v1` 至 `v6` 保留开发中的误拒答、校验失败与修复结果；`v5` 是中断的部分记录。
完整性以各目录的 `summary.json` 为准，部分 JSONL 不能冒充全量成绩。

[最终 310 题端到端结果](evaluation/results/techqa_semantic_v3/summary.json) 全部完成，执行异常为 0。
Y 正文 F1 为 0.21303，Y 接受率为 0.7875，N 标签拒答比例为 0.10；仍有 2 题输出验证失败，
未发布答案且不计拒答成功。正文质量基本持平，不能因修复了若干误拒答案例就声称生产质量通过。
[完整状态核验](evaluation/results/techqa_semantic_v3/validation.json) 另列输出失败和后端降级数量。

TechQA 原始 N 标签的范围是官方候选 DOC_IDS；全库开放检索的拒答数字是代理指标，不是官方候选集 QA 评分。
完整 Dense/BM25/Hybrid 对比和训练阈值见父 README 与 `evals/techqa_semantic_full`。
单元测试只使用提交的官方原文小样本，不依赖本机下载目录。
