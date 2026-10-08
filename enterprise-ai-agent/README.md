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
原文片段通常为 900 字符；引导句后的完整指令组可扩展至 1800 字符，仍受序列化 Context 预算约束。
超过预算的指令组不截断发布。压缩前排除明确的操作/组件冲突，以及同一产品的较旧最低版本错误前提。
Query Rewrite 保留带版本的包名，并先检索明确的 API、错误码和版本比较问题。
校验重试携带具体错误与合法来源 ID；`trace.validation_failures` 保留失败诊断，最终仍失败则拒答。

## 评测

```powershell
$env:AGENT_PROFILE = "ollama"
python -m evaluation.evaluate --output evaluation/results/techqa_semantic_v4
# 中断后以相同数据、代码和模型续跑；失败记录仍保留
python -m evaluation.evaluate --output evaluation/results/techqa_semantic_v4 --resume
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

[整改前已归档的 310 题端到端结果](evaluation/results/techqa_semantic_v3/summary.json) 全部完成，执行异常为 0。
Y 正文 F1 为 0.21303，Y 接受率为 0.7875，N 标签拒答比例为 0.10；仍有 2 题输出验证失败，
未发布答案且不计拒答成功。正文质量基本持平，不能因修复了若干误拒答案例就声称生产质量通过。
[完整状态核验](evaluation/results/techqa_semantic_v3/validation.json) 另列输出失败和后端降级数量。
这些完整开发集数字对应此前代码版本，不能当成本轮整改后的全量成绩。
本轮使用 `data/techqa/regression` 的 16 条原始开发题回归，并继续检索完整知识库；
从父目录运行 `./scripts/run-remediation-checks.ps1` 可串行复验 Enterprise、Agent 比较、Critic 和 HTTP。
每次默认生成新的结果目录，保留此前完整结果与失败轨迹。回归集包含已知失败，不是独立盲测。
[本轮完整 16 题回归](evaluation/results/techqa_remediation_v4/summary.json) 执行异常与最终校验失败均为 0。
相同 16 题的 Y 正文 F1 从 0.4295 至 0.4619；安装版本题仍安全拒答，不能算已解决。
完整对比、N 标签指标下降及剩余问题见父目录 [整改报告](../audit/2026-10-03-targeted-remediation.md)。

TechQA 原始 N 标签的范围是官方候选 DOC_IDS；全库开放检索的拒答数字是代理指标，不是官方候选集 QA 评分。
完整 Dense/BM25/Hybrid 对比和训练阈值见父 README 与 `evals/techqa_semantic_full`。
单元测试只使用提交的官方原文小样本，不依赖本机下载目录。

## Project 2：技术支持知识分析（Chap12–15）

新版入口为 `api.project2_runtime_main:app`；原 `api.main:app` 与旧
`MultiAgentVersion` 默认行为保留。Supervisor 顺序调用已有 RAG Worker 和
`techqa_document_query` Database Worker。后者对官方 TechQA 全文 SQLite 做
参数化只读查询，不使用检索候选或模型结果计算文档数。文档数不是工单量、故障率或销量。
不采用业务写操作、Fake Publish、Text-to-SQL、MCP/A2A、Queue 和新结果缓存。

本地运行（父仓库已安装现有依赖、全量官方索引与本地模型）：

```powershell
# 在 enterprise-ai-agent 目录运行；凭证由本机服务管理员设置。
# 从 .env.example 的占位示例填写 PROJECT2_CREDENTIALS_JSON，勿提交真实值。
$env:PYTHONPATH = "../src;."
../.venv312/Scripts/python.exe -m uvicorn api.project2_runtime_main:app --host 127.0.0.1 --port 8012
```

`GET /healthz` 的 `ready=true` 只在全量索引、嵌入模型加载和预热完成后返回。
请求为 `POST /v1/project2/analysis`（或 `/v2/project2/analysis`），必须携带
`Authorization: Bearer <本机配置的令牌>`；正文不能授予主体、资源或操作权限：

```json
{"query":"Does ODM 8.5.1 support MQ 9.0?\n\n\nDoes ODM 8.5.1 support MQ 9.0 where ODM Rule Execution Server is running on WAS 8.5.0.2 (embedded with ODM)?\n\nNo MQ version is specified in ODM 8.5.1 System Requirements.","analysis_operation":"compare_document_counts","include_samples":true,"sample_limit":5}
```

上述输入来自预登记的官方 TechQA 原问题，实际验收使用同一登记集合。
成功响应包含 `run_id`、六态 `status`、`workers`、`data_results`、`answer`、
`evidence`、`usage`、`limitations`。`partial` 明确列出缺口，不计入完整回答。
两 Worker 状态由程序按冻结 S07 矩阵汇合；`completed` 不表示事实评分正确。
默认硬预算为19次依赖尝试、6次LLM尝试、90秒累计执行时间；恢复不清零，
停机时间不计入执行时间，运行存活上限15分钟。

状态读取：`GET /v2/project2/runs/{run_id}`；恢复：
`POST /v2/project2/runs/{run_id}/resume`；Trace：
`GET /v2/project2/runs/{run_id}/trace`。均重新验权，未知运行、非 owner 和非法状态
明确失败，已完成节点跳过。Checkpoint保留24小时，Trace保留7天；内部状态写入不是业务发布。

容器命令从父仓库执行：

```powershell
# .container-secrets.env 使用本机凭证，已被 Git 与构建上下文排除。
docker compose -f containers/project2/compose.yaml build --no-cache
docker compose -f containers/project2/compose.yaml up -d --no-build --pull never
Invoke-RestMethod http://127.0.0.1:18012/healthz
docker compose -f containers/project2/compose.yaml logs --no-color api
docker compose -f containers/project2/compose.yaml stop api
# 再启动不删除保留卷；不要使用 down -v。
docker compose -f containers/project2/compose.yaml start api
```

镜像使用锁定 digest 的 Python3.12基础镜像和已校验哈希的 Linux wheelhouse，
不复制宿主 `.venv`。Dockerfile 离线安装；新机器必须先准备相同构建材料。
全量 SQLite、约309万 Chunk 的向量/元数据索引及 MiniLM 模型只读挂载，不塞进镜像。
API写层为临时文件；`state`、`logs`、`rerank_cache` 是保留的命名卷。
仅映射本机18012端口，Ollama通过 `host.docker.internal:11434` 访问已有主机模型。
6GB容器内存限制、实际大索引挂载与恢复限制见
[容器可行性](../containers/project2/container_feasibility.md)。

可复验的作业证据：

- [Chap12工程门禁](../audit/project2-v1/v031_chap12_gate.json) 与
  [Chap13真实子进程恢复门禁](../audit/project2-v1/v033_chap13_gate.json)。
- [本轮Chap14真实门禁](../audit/assignment-completion-20261007/container_gate_final/gate.json)：
  干净构建、真实组合请求、独立计数、日志诊断、停止保留卷、重启恢复与owner隔离。
- [Chap11原RAG/Agentic同集对照](../audit/assignment-completion-20261007/chap11/summary.corrected.json)、
  [可靠性改动前](../audit/assignment-completion-20261007/reliability_before/summary.json) 与
  [改动后](../audit/assignment-completion-20261007/reliability_after/summary.json)。
  固定官方tune问题、三重复；异常保留在分母，报告CI、范围、调用与延迟，不预设新版本更好。

现有回归入口为父仓库 `python scripts/test_all.py`；规格检查为
`python specs/project2/v0.3.4/check_docs.py`。历史37.941秒与当前90秒成绩分开保存。
S14质量验收仍未通过、人工盲评待办；不把架构/容器门禁替代答案质量验收。
第16章云部署及远端Feature PR/Review尚未执行，受当前用户禁止云操作/push/PR的边界限制。

Chap15 选定依赖是既有 SQLite 查询、检索/重排缓存及本机模型。缓存键含模型名、
完整输入文本、已验证的文档/语义索引版本和服务端主体/租户/权限范围的哈希。
验权发生在缓存访问前；没有可信上下文的内部调用不读取缓存。旧无范围键保留，
新版不复用这些条目。不是新增答案缓存，不缓存授权决定或模型完整回答。

| 故障 | 有界处理 | 返回语义 |
| --- | --- | --- |
| 无效输入、拒权、策略/数据版本冲突 | 零次重试；不发起禁止操作 | failed / permission_denied，缺能力有明确原因 |
| SQLite语句/Worker超时 | 12秒/25秒本地限制，受90秒总执行期限约束；DB不自动重试 | 已有计数保留，其余为null；partial/timeout |
| 模型/HTTP超时 | 单尝试30秒，受请求总预算约束；取消所拥有的隔离Worker | 保留DB结果，RAG timeout/failed，按S07汇合 |
| 依赖或LLM预算耗尽 | 第20次依赖/第7次LLM不启动；已返回终态的闲置Worker保持就绪 | 明确记录预算错误，保留DB结果并按S07汇合 |
| 无效结构或引用 | 沿用既有一次格式修复；仍受总预算限制 | 失败后拒答，不伪造来源或标完整成功 |
| 旧缓存版本或其他主体范围 | 使用不同键，不读其他范围条目；同范围有效命中保留 | 真实模型重新计算，调用如实计入预算 |

不新增无限重试、Circuit Breaker、Queue、并行或结果Cache；无业务写入，不虚构
发布幂等成绩。[真实故障复测](../audit/assignment-completion-20261007/reliability_fault/gate.json)
使用官方原文及真实SQLite/本机嵌入模型；保留注入故障、定位和相同条件复测证据。
该修复隔离旧版本/不同范围缓存，不声称能够检测任何任意的缓存内容损坏。
前测保留既有缓存；后测使用预登记的空命名空间，原缓存与失败试验记录均保留。
新命名空间首轮有效缓存较冷，后续轮次逐渐命中，
必须结合分轮调用与延迟报告，不能把冷热差异宣称为性能收益。

相同50个官方tune任务、各三重复的实际可靠性对照：

| 指标 | 修改前（既有缓存） | 修改后（新范围缓存） |
| --- | --- | --- |
| Worker timeout/failed | 0.020；3.00/150；95%CI [0.004, 0.105]；三轮范围 [0.020, 0.020] | 0.060；9.00/150；95%CI [0.004, 0.262]；三轮范围 [0.020, 0.140] |
| 平均秒数 | 15.154；2273.09/150；95%CI [13.712, 16.587]；三轮范围 [13.044, 18.272] | 15.118；2267.72/150；95%CI [13.723, 16.533]；三轮范围 [13.291, 18.308] |
| 平均LLM尝试数 | 2.900；435.00/150；95%CI [2.740, 3.040]；三轮范围 [2.900, 2.900] | 2.847；427.00/150；95%CI [2.693, 2.973]；三轮范围 [2.740, 2.900] |

失败题次从3/150至9/150。新增失败集中在新范围冷缓存的首轮预算耗尽；不抬高19/6/90硬上限、不剔除失败，不宣称可靠性或性能更好。后两轮的缓存状态与首轮不同。
CI按独立问题组计算；重复题次不作为独立问题扩充分母。Token/货币Cost在本机路径没有暴露完整可信值时保持null。

Chap11固定39题（29 Y + 10 N）同集三重复、234次真实请求：

| 指标 | 原RAG | Agentic RAG |
| --- | --- | --- |
| 正文F1（代理） | 0.193；16.77/87；95%CI [0.126, 0.267]；三轮范围 [0.193, 0.193] | 0.457；39.73/87；95%CI [0.335, 0.571]；三轮范围 [0.457, 0.457] |
| 返回候选R@5 | 0.552；48.00/87；95%CI [0.375, 0.716]；三轮范围 [0.552, 0.552] | 0.552；48.00/87；95%CI [0.375, 0.716]；三轮范围 [0.552, 0.552] |
| N题明确拒答 | 0.300；9.00/30；95%CI [0.108, 0.603]；三轮范围 [0.300, 0.300] | 0.000；0.00/30；95%CI [0.000, 0.278]；三轮范围 [0.000, 0.000] |
| 平均LLM尝试数 | 1.265；148.00/117；95%CI [1.026, 1.513]；三轮范围 [1.231, 1.282] | 2.983；349.00/117；95%CI [2.863, 3.128]；三轮范围 [2.949, 3.000] |
| 平均秒数 | 36.429；4262.17/117；95%CI [27.551, 45.961]；三轮范围 [32.018, 44.554] | 25.171；2944.99/117；95%CI [19.604, 32.042]；三轮范围 [17.754, 39.726] |
| 输出校验失败 | 0.077；9.00/117；95%CI [0.027, 0.203]；三轮范围 [0.077, 0.077] | 0.000；0.00/117；95%CI [0.000, 0.090]；三轮范围 [0.000, 0.000] |

正文F1只对生成正文评分，不把source文本加入答案；它不等于required_facts覆盖率或生产质量。样本2, 7, 8, 16, 37的Agentic正文F1下降；Agentic N题拒答0/30，不声称整体质量更好。分类型结果、全部失败和逐题差异见上述JSON。原RAG的生成Token未被观察器保存，不能进行可信Token或货币Cost比较。
原始HTTP调用分类和拒答状态观察器有误，已依据保留的API路径/源码契约仅作离线更正；原始请求和汇总原样保留，不重跑模型。
额外空检索示例使用预登记的语言过滤：真实返回空候选、零来源、零confidence和拒答；这是过滤故障注入，不是无过滤N题质量证明。该额外请求经历约两小时墙钟间隔，其7234.233秒耗时不纳入234次对照或正常延迟结论；主对照的防睡眠心跳无间隔异常。见[异常耗时记录](../audit/assignment-completion-20261007/chap11/empty_retrieval_timing.json)。
