# Enterprise TechQA Agent

这是同一仓库的 Agent Service。默认 Retriever 使用父项目 `rag.techqa` 共享全量检索：
既有 Qdrant Hash Dense + 全量 SQLite FTS5 BM25 + RRF + 有限候选 nomic 语义重排。
保留 Rewrite、Parent 获取、Context Compression、引用逐字验证与 answer/sources/confidence 输出。

## 获取全量官方数据

先在父目录安装 `pip install -e ".[dev,api]"`，运行 `scripts/start-local.ps1 -FullTechQA`。
然后从本目录执行：

```powershell
$env:AGENT_PROFILE = "offline"
$env:AGENT_EMBEDDING_PROVIDER = "hash"
$env:AGENT_QDRANT_URL = "http://localhost:6333"
$env:AGENT_COLLECTION = "techqa_full_hash"
python -m vectorstore.seed --scope full --chunk-size 1200 --chunk-overlap 160 --batch-size 128
python -m vectorstore.indexes
cd ..
python -m rag.techqa.index --scope full
python scripts/verify_techqa_source.py
```

seed 自动下载官方 GitHub 指向的 PrimeQA/TechQA tar.gz，校验固定 SHA-256 后安全解包、流式读取并幂等写入。
断点重复执行会在 Embedding 前跳过已经存在的文本哈希。原始文件位于 `data/techqa/extracted/TechQA`，
已被 Git 忽略。全量源文件 801,998 条，2 条正文为空；实际全文索引 801,996 篇，详见父目录
`evals/techqa_source_inventory.json`。Qdrant 当前 2,826,591 个去重后的向量 Chunk。

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
共享服务的全量配置由 `TECHQA_QDRANT_URL/TECHQA_COLLECTION/TECHQA_INDEX_PATH` 决定。

API：`POST /v1/agent/query`，请求：

```json
{"query":"How are Streams environment variables set after upgrade to 4.1.1.2?","filters":{"language":"en"}}
```

响应仅包含 `answer`、`sources`、`confidence`。无证据时 confidence=0。
最终 Top-k 之后取回 TechNote Parent，优先保留完整解决步骤及命令参数，避免只返回问题描述。
LLM 只能选择本次证据中的完整原文，引用内容或 ID 不合法时修复一次，仍不合法则拒答。

## 评测

```powershell
$env:AGENT_PROFILE = "offline"
python -m evaluation.evaluate --output evaluation/results/techqa_shared
# 三个服务和全部 Agent 端点的真实模型 HTTP 复验：从父目录执行
python scripts/smoke_techqa.py
```

[共享检索后的完整开发集结果](evaluation/results/techqa_shared/summary.json) 对应官方 310 题。
[原始逐题记录](evaluation/results/techqa_shared/runs.json) 保留答案、引用、拒答、延迟和错误；异常记零并留在分母。
`evaluation/results/full_hash_remediation` 是改进前真实全量 Hash 基线，不是当前默认流程。

TechQA 原始 N 标签的范围是官方候选 DOC_IDS；全库开放检索的拒答数字是代理指标，不是官方候选集 QA 评分。
完整 Dense/BM25/Hybrid 对比和训练阈值见父 README 与 `evals/techqa_full`。
单元测试只使用提交的官方原文小样本，不依赖本机下载目录。
