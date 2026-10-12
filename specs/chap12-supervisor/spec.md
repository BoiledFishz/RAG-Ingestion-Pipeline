# Chap12 Supervisor–Worker（精简版）规格

状态：**实现已完成，待人工审阅**。本规格与实现同批交付，未经过“先审阅后实现”的流程；请审阅后再合并。
分支：`feature/chap12-supervisor-lite`。与 `specs/project2/` 的 v0.x 系列相互独立，不修改其中任何文件。

## 1. 范围与数据

- 数据：从官方 TechQA `training_Q_A.json` 中以固定种子 `20261011` 随机抽取 **150 题**（123 Y / 27 N）。
  语料为这 150 题官方 `DOC_IDS`（每题 50 篇候选：答案文档加官方干扰文档）的并集，共 **6,612 篇**，全部来自官方全文库，无合成文本。
- 选 training 而不选 dev：dev 的 held-out 部分按既有协议封存，本作业不触碰。
  已知偏差：复用的 Project 1 检索阈值是在 training 上标定的，所以 RAG 的绝对指标偏乐观；两个对照系统使用同一阈值，比较仍然公平。
- 产物（构建命令 `python -m evaluation.chap12_build_sample`）：
  - `.rag_data/chap12_sample.sqlite`：`docs` + FTS5 `search` + `vocabulary` + `manifest`（与 Project 1 `TechQAIndex` 同一 schema），另有结构化表 `technotes`、`document_products`；
  - `enterprise-ai-agent/evaluation/chap12/tasks.jsonl`：任务（只含问题文本）；
  - `.../gold.jsonl`：答案、标签、金标文档，**只供离线评分使用**，两个系统都读不到；
  - `.../sample_manifest.json`：种子、题号、源文件和索引的 SHA256。

## 2. 拓扑

```mermaid
flowchart TD
    U[POST /v1/chap12/analyze] --> A[服务端凭证 → TrustedContext]
    A --> S[Supervisor：校验 / 计划 / 预算]
    S -->|RagInput: query| R[RAG Worker<br/>复用 Project 1 RAGAgent]
    S -->|DbInput: 操作+产品+时间| D[Database Query Worker<br/>参数化只读模板]
    R --> M[程序汇合状态与证据]
    D --> M
    M --> F[FinalResponse]
```

- Supervisor 的计划是确定性的：`goal` 是一个枚举，`explain → [rag]`，`data → [database]`，`explain_and_data → [rag, database]`。不使用 LLM Planner，也没有 Replan。
- RAG 和 DB 之间没有数据依赖，所以**并行执行**（`asyncio`）。每个 Worker 只返回自己的结果对象，Supervisor 在两者都结束或总截止时间到达后才汇合，因此不存在共享 State 的写冲突。
- 模型可能参与的环节只有复用 RAG 内部的改写和证据选择。节点、工具和权限都由程序决定。

## 3. Worker 选型

| 候选 | 结论 | 理由 |
| --- | --- | --- |
| Database Query Worker | **采用** | 样本文档带有官方 metadata（productId/productName/date），可以构造真实的结构化查询；结果可以独立复算 |
| Analytics/Forecast | 不采用 | 没有业务时间序列或观测量，预测会是编造的 |
| Domain/API | 不采用 | 没有项目真正需要的外部服务 |
| Evidence Reviewer | 不采用 | Project 1 已有程序化引用校验和适用性复核；另做一个 Reviewer 只会重复这些检查 |

## 4. Contract（`agents/chap12/contracts.py`，版本 `chap12-v1`）

- `AnalysisRequest{query, goal, data_request?}`：拒绝未知字段，请求正文**不能**携带身份或权限。
- `DataRequest/DbInput{operation ∈ count_documents|count_by_year|list_recent_documents, product, date_from, date_to, doc_class, limit≤10}`。
- `TrustedContext{subject_id, tenant_id, allowed_workers, allowed_db_operations, allowed_product_ids}`：只由服务端根据凭证的 SHA256 映射构造（环境变量 `CHAP12_CREDENTIALS_JSON`）。
- `WorkerResult{contract_version, run_id, task_id, worker, status, payload, limitations, error{category, message, retryable}, usage}`。
  校验规则：`completed`/`partial` 必须带 payload；`permission_denied`/`timeout`/`failed` 必须带 error。
- RAG payload：answer、citations（source_id、doc_id、quote）、confidence、rag_status、rewritten_query、retrieved_doc_ids。
- DB payload：operation、产品名与 ID、时间范围、doc_class、metric（口径）、unit、count/rows、truncated、snapshot、query_template。
- `FinalResponse`：status、plan、answer、citations、data_result、limitations、worker_results、usage、trace。

### 状态定义

| Worker | completed | partial | no_data | permission_denied | timeout | failed |
| --- | --- | --- | --- | --- | --- | --- |
| RAG | 回答带有经过校验的引用 | 只回答了一部分 | 拒答或需要澄清 | 主体无 RAG 权限 | 超过截止时间 | 证据校验失败、依赖不可用、预算耗尽 |
| DB | 查询完整成功，**计数为 0 也算**（审阅决定 D1） | 按年分组结果超过 40 行被截断 | 列表查询返回空列表，或无法确定产品（clarification_required） | 操作或产品不在授权范围 | 截止时间到达（语句被中断，或线程在截止后试图发起新语句） | 参数非法、依赖错误、预算耗尽 |

### 汇合规则

两个任务都是必需的：

- 都是 completed → completed；
- 只要有一个是 completed 或 partial → partial，并在限制说明里列出缺失部分；
- 否则按 permission_denied > timeout > failed > no_data 的优先级取。

全部 36 种组合都有测试覆盖。凭证有效但没有任何 Worker 权限时，直接返回 permission_denied，不调用任何 Worker。

## 5. 权限、白名单与规模限制

- DB：不支持 Text-to-SQL。只有 3 个程序持有的参数化 SQL 模板，连接以 `mode=ro` 打开并设置 `PRAGMA query_only`。
  产品必须能在快照目录里精确匹配，否则在执行任何 SQL 之前就以 invalid_input 拒绝。
  每条查询都会带上授权的产品条件；越权时只返回 permission_denied，不透露数据是否存在。
  `list_recent_documents` 的 limit 不超过 10，按年分组不超过 40 行。
- RAG（审阅决定 D3，检索时过滤）：RagWorker 把 `TrustedContext.allowed_product_ids` 写入请求范围的 ContextVar。BM25 和 dense 两路都包了一层 `ScopedRetriever`：先多取（limit × 20，上限 1000），再按 `document_products` 只保留授权产品的文档，然后才进入 RRF 和重排，所以未授权文档不会进入重排器、父文档解析或 LLM 上下文。父文档展开前还会再检查一次，越界就抛错。受限主体的结果中会附带限制说明。DB 的产品推断也只在授权文档中进行，拒权时不会透露问题与哪个未授权产品相似。
- 沿用 Project 1 的过滤白名单和 `published` 强制过滤。检索范围限定在样本内：BM25 加上样本自己的 MiniLM 向量（从 Project 1 全量向量中复制），经 RRF 混合后重排。重排在 offline 档位用 MiniLM，在 ollama 档位默认用 nomic。全库 dense 服务会越出样本范围，所以不使用。

## 6. 预算与终止（`budget.py`、`metered.py`，Contract chap12-v2）

每个请求有一个绝对截止时间，并按类别设置调用上限，默认值为：

| 类别 | 含义 | 默认上限 |
| --- | --- | --- |
| llm | 模型生成调用 | 8 |
| embedding | nomic embedding 请求（缓存未命中的批次） | 4 |
| db | DB Worker 的逻辑查询和产品推断 | 4 |
| tool | Worker 调用 | 4 |
| sql | **每一条** SQL 语句，包括 RAG 的 BM25、父文档查询和 DB Worker 的语句 | 400 |
| local | 本地模型计算（MiniLM 查询编码） | 16 |

另外记录 nomic 缓存命中的文本数（`embedding_cache_hits`）。命中不产生外部调用，不设上限。截止时间默认 150 s。所有上限都可以用环境变量 `CHAP12_*` 修改；默认值由审阅决定 D4 确认。

- **调用前预留**：每次调用在开始前预留额度，失败、重试和取消的调用都计数。计数通过 ContextVar 进入复用的模型、重排 embedder、Project 1 的 `TechQAIndex`（由 `MeteredIndex` 包装每条语句）以及 MiniLM 编码，不修改 Project 1 代码。
- **线程内的截止语义（P0-3）**：检索、编码和 SQL 在 `asyncio.to_thread` 的线程里运行。到截止时间时，Supervisor 取消等待中的协程，但无法终止已经开始的线程。因此：
  - 每条 SQL、每次 LLM/embedding/本地编码调用前都调用 `charge()`；截止时间一过，它就抛出 `BudgetExhausted(deadline)`，被放弃的线程不能再发起新的调用；
  - 正在执行的 SQL 由 progress handler 在截止时间中断；
  - 已经开始的单次本地计算（例如一次编码）会继续跑完，但结果被丢弃。
- **重试**：DB 遇到 locked/busy 最多重试 1 次；RAG 证据校验重试沿用 Project 1 的上限（1 次）。
- Token 数：复用的 Ollama 适配层不返回 token。真实档位的采集方式见 P0-4。

## 7. 非目标

不做 Text-to-SQL、LLM Planner/Replan、Critic、写操作或 HITL、MCP/A2A、新的结果缓存，也不改动 Project 1 代码或旧的 `api.main`。

## 8. 已知限制

- 产品槽位优先使用问题中**字面出现**的目录产品名；没有时由 DB Worker 用自己的 BM25 前 3 篇文档推断，结果标注 `product_source=inferred`。推断仍无结果时返回 `no_data/clarification_required`。详见 `improvements.md`。
- 文档计数只反映样本快照的覆盖情况，不代表 IBM 全量知识库，也不是故障率或工单量。
