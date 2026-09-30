# 作业要求与流程验收报告

验收日期：2026-09-29（America/Los_Angeles）。依据为本次对话提供的原始作业题目，以及三个项目的 README。检查对象为当前工作区；主分支提交为 `38c9597`，另有未提交修改和两个未跟踪的 Agent 项目。

**结论：主要功能已经实现，离线主流程多数能复现；目前不能判定为“全部要求完成、所有流程都能跑通”。主要缺口是默认运行环境、失败状态处理、降级后的阈值、Agent 评测有效性，以及 Git 提交与干净环境复现。**

## 1. 哪些要求属于哪个项目

| 原始要求 | 对应实现 | 本次判断 |
|---|---|---|
| 生产级 PDF/Markdown Ingestion | 根目录 `main.py`、`utils.py`、`src/rag/ingestion` | 主体实现完整；默认 Embedding 依赖缺失，失败退出码有缺陷 |
| Dense → Rerank → Hybrid、Context/Citation、HTTP API、15 题评测及三阶段 Tag | 根目录 `src/rag/retrieval`、`generation`、`api`、`evals` | 主要功能和阶段标签存在；正常路径可运行，端到端降级有缺陷 |
| 作业 1：Agentic RAG Service | `enterprise-ai-agent` | 所需四项功能及三类问题测试已实现；当前 core 库可查询，提交与复现尚未完成 |
| Task 1–4：LLM Planner、ReAct、Critic、Single/Multi 对比 | `agentic-rag-homework` | 结构与接口已实现；真实模型表现和对比报告仍有重要缺口 |

IBM TechQA 全量 801,998 篇导入是项目自行增加的功能，不是原始题目中的必交数量要求。全量服务不可用属于现有附加流程问题，不据此单独判定原始作业不合格。不同作业的规范也不机械混用：例如根项目生产代码禁止 `print()`，不能据此直接判定独立 Agent 实验报告打印器违规。

## 2. 实际运行结果

| 检查 | 本次结果 | 验证范围 |
|---|---|---|
| 根目录按 README 执行 `python -m pytest` | **失败：6 个收集/导入错误** | 根配置把独立子项目一起收集 |
| 根项目 `python -m pytest tests test_pipeline.py` | **24 passed** | 主流水线、检索、过滤、重排、引用、OCR 分支等 |
| Agentic 子项目 `python -m pytest` | **12 passed** | Planner、Research、Critic、API、比较逻辑 |
| Enterprise 子项目 `python -m pytest -q` | **34 passed** | 当前机器已具有官方数据的环境 |
| Enterprise 干净源码副本、无忽略的数据目录 | **33 passed，1 failed** | 官方 dev JSON 缺失导致测试失败 |
| Ruff | **三个项目都通过** | 根项目显式检查生产代码、测试、入口和 evals |
| MyPy | **根项目 28 文件通过；Enterprise 25 文件通过** | Agentic 项目未声明严格 MyPy 验收流程 |
| `pip check` | **两个现有虚拟环境都通过** | `.venv`、`.venv312` |
| 三个 Tag 的独立源码快照测试 | **11 / 12 / 18 passed** | 分别为 v1-dense / v2-rerank / v3-hybrid；使用现有依赖环境 |
| 混合格式真实导入 | **成功** | 6 文件中 4 个有效文档成功，空文件和损坏 PDF 跳过；6 个有效页面、28 个 512-size Chunk |
| OCR | **成功** | 扫描 PDF 第 1、2 页通过本机 Tesseract 识别 |
| 幂等重跑 | **成功** | 28 个 Chunk 全部跳过摘要与 Embedding；必需元数据完整 |
| 真实 Ollama 摘要及入库 | **调用/入库成功，句子完整性有缺陷** | 单 Chunk 文档完成 LLM 摘要 + Hash Embedding + Qdrant 入库，`summary_fallback=false`；实际摘要被 240 字符上限截断到半个单词 |
| 默认 Ollama Embedding | **失败** | 缺少 `nomic-embed-text`，`/api/embed` 返回 404 |
| 根 RAG HTTP API | **三种模式可运行，质量存在问题** | 本次使用 Hash Embedding + 真实 Ollama 生成；Dense 的 EC2 问题和 Sparse/Hybrid 的 S3 问题返回带引用回答，未知问题/空过滤结果拒答，空 query 返回 422；S3 问题在 Dense 下被阈值拒答 |
| Agentic Demo HTTP API | **8 个请求全部 HTTP 200** | RAG 三类问题 + Planner、Research、Single、Multi、Critic |
| Agentic Ollama HTTP API | **8 个请求全部 HTTP 200，但并非全部答对** | 真实 Planner 可返回计划；EKS Research/Single/Multi 均未找到已有外部证据；Critic 达到两次重试后失败 |
| 真实 Planner 稳定性 | **10/10 通过 Schema/Agent 校验** | 同一任务、`llama3.2:3b`、temperature=0；这是单任务重复试验，不代表所有问题均稳定 |
| Enterprise core HTTP API | **三类问题可运行** | 真实本地 `techqa_hash` 有 117,580 个点；IBM Streams 问题返回来源，模糊问题澄清，PostgreSQL XX999 问题拒答 |
| Enterprise 原有 `evaluation.smoke_api` | **失败** | 查询 WebSphere，却要求答案含 `900`，断言与现有 TechQA 数据不匹配 |
| TechQA 官方 310 题评测 | **完整运行成功，0 个运行错误** | core / hash；160 可回答 + 150 不可回答；Hit@5=0.4875、Hit@10=0.5250、MRR=0.4239、拒答准确率=0.3933、平均 2583.85 ms |
| 全量 TechQA HTTP/Qdrant 流程 | **当前环境无法运行** | `127.0.0.1:6333` 拒绝连接，Docker daemon 管道不存在；未重新导入全量库 |

本次开启的 API 都使用临时端口，检查后关闭；评测输出和测试数据库使用独立审计目录。没有把 Hash Embedding、模拟模型或 HTTP 200 本身当成语义检索与答案正确性的证明。

## 3. Ingestion 作业逐项核对

| 要求 | 状态 | 证据/说明 |
|---|---|---|
| PDF + Markdown 混合解析 | 通过 | `src/rag/ingestion/utils.py`，真实混合语料验证 |
| 无文本时自动 OCR | 通过 | `DocumentParser` 原生文本阈值分支，扫描 PDF 两页验证 |
| RecursiveCharacterTextSplitter | 通过 | `src/rag/ingestion/chunking.py`，使用递归分隔符 |
| source_file/page_number/SHA-256 chunk_hash | 通过 | 28 个实际入库 Chunk 全部具有要求字段 |
| LLM 一句话 context_summary | **部分通过** | 真实 LLM 摘要已随 Chunk 入库，但超长摘要会被截成不完整句子，见问题 8；该检查使用 Hash Embedding，默认语义 Embedding 全链路仍受模型缺失阻塞 |
| Embedding 之前库内检查 hash | 通过 | 第二次导入直接跳过 28 个 Chunk，没有再次摘要或 Embedding |
| 单文件损坏不终止整条流水线 | 通过 | 损坏 PDF 与空文档被跳过，其余 4 文档入库 |
| 类型提示、异步批量请求 | 通过 | MyPy 通过；摘要与 Embedding 使用并发限制和 `asyncio.gather` |
| logging、每文件 INFO、异常日志 | 通过 | 生产路径使用 logging；实际日志有文件处理与损坏文件记录 |
| 指定两个 pytest 测试及文件结构 | 通过 | `test_pipeline.py` 包含清洗、空/坏文件测试；`main.py`、`utils.py` 存在 |
| 5 题黄金集、Ragas Context Recall、两组参数 | 通过 | 本次重新运行 `.venv312` 下的 Ragas 评测 |
| README 参数表及生产推荐理由 | 通过 | 256/512 对比、512/64 推荐与合成集局限均已说明 |
| 可据退出状态判断成功 | **不通过** | Embedding 失败、未入库仍退出 0，见问题 1 |

本次 Ragas 结果：

| 数据集 | Chunk Size | Chunk 数 | Context Recall@3 |
|---|---:|---:|---:|
| 5 题合成集 `data/my_docs` | 256 | 17 | 1.00 |
| 同上 | 512 | 8 | 1.00 |
| 混合格式压力集 | 256 | 59 | 0.50 |
| 同上 | 512 | 28 | 0.40 |

## 4. Retriever 作业逐项核对

| 要求 | 状态 | 证据/说明 |
|---|---|---|
| DenseRetriever 读取已有向量库；candidate_k/final_k 可配置 | 通过 | `dense.py`、`pipeline.py` 及持久化 metadata 测试 |
| source_file/document_type/language/status 过滤 | 通过 | `FilterPolicy`；Dense 与 Sparse 共享过滤策略 |
| status=published 不可覆盖 | 通过 | 指定安全过滤单测通过 |
| 六个必需检索结果字段 | 通过 | `SearchResult.to_dict()` 与 Dense 测试 |
| BaseReranker 接口；Query/正文/summary；原始及精排排名分数 | 通过（实现） | Lexical 与 CrossEncoder Adapter 均存在；CrossEncoder 本次只验证现有注入式单测，未真实加载模型 |
| Dense 30 → Rerank 20 → Final 5；空候选不调用重排 | 通过 | 专用候选上限及顺序测试通过 |
| Reranker 超时降级 | **检索层通过，完整服务不通过** | RRF 分数被错误套用精排阈值，见问题 2 |
| 三种模式、同 chunk_id 的 BM25、相同过滤 | 通过 | API、单测、15 题四模式评测验证 |
| gather 并行、手写 RRF、去重、完整排名来源、融合后仅重排一次 | 通过 | `pipeline.py`、`fusion.py` 及对应测试 |
| Dense/BM25 单路故障可降级 | 通过（检索层） | 单路失败测试通过；相关性阈值仍需对应最终分数空间 |
| Context Budget、同源最多 2 块、最终结果后扩展 Parent | 通过（现有实现与测试） | `ContextBuilder` 与 Parent 测试；token 数是正则估算，非目标模型 tokenizer 的精确长度 |
| 外部数据 Prompt、source_map 校验、一次引用修复后拒答 | 通过（ID 校验） | 空结果/低分/非法来源测试通过；不等于逐句事实有证据支持 |
| logging、类型提示、配置、接口隔离、环境变量 | 通过（主要代码规范） | Ruff、MyPy 通过，配置项和 Adapter 接口齐全 |
| POST /v1/rag/query | 通过（受控配置） | Hash 向量 + 真实 Ollama 的 HTTP 检查完成；默认语义 Embedding 依赖缺失 |
| 六个指定名称的核心测试 | 通过 | RRF、去重、安全过滤、重排降级、非法引用、Context Budget 测试均存在并通过 |
| 15 题类别与必需指标 | 通过 | 5 语义 + 4 错误码/API/产品 + 3 Filter + 3 不可回答 |
| README 架构/数据流/对比/公式/降级/成功与拒答/参数理由 | 通过 | 所需内容均存在 |
| 三个阶段 Tag 独立代码 | 本地通过 | 三个 Tag 存在且快照测试通过；远端发布状态未核实 |

本次 15 题结果（Hash Embedding、Lexical Reranker）：

| 模式 | Recall@5 | Recall@10 | MRR | Context Precision | 平均延迟 ms | 拒答准确率 |
|---|---:|---:|---:|---:|---:|---:|
| Dense | 0.750 | 0.917 | 0.608 | 0.150 | 3.13 | 1.000 |
| Dense + Rerank | 0.750 | 0.917 | 0.626 | 0.150 | 3.78 | 1.000 |
| Sparse + Rerank（附加） | 0.750 | 0.917 | 0.617 | 0.150 | 0.94 | 1.000 |
| Hybrid + Rerank | 0.750 | 0.917 | 0.613 | 0.150 | 4.11 | 1.000 |

该小集每道可回答题当前均只对应 1 个证据 Chunk，已额外核对 Recall 分母；表中 Recall 与当前证据集一致。拒答阈值是在同一 15 题集上校准的，不能据此推断独立测试集也有 100% 拒答准确率。

## 5. Agent 作业逐项核对

| 要求 | 状态 | 判断 |
|---|---|---|
| Enterprise 目录结构 | 通过 | api、agents/rag_agent、tools/retriever、vectorstore、models、evaluation、tests 齐全 |
| Query Rewrite | 通过（实现及测试） | Rule/LLM 两种重写器；保护产品名、错误码、数字与否定词，校验失败可回退 |
| Retriever Tool 封装 Vector DB | 通过 | 实际使用 core Qdrant 数据进行 HTTP 查询 |
| Top-k → Relevant Context | 通过（实现及测试） | 相关句抽取、预算、最多来源数、同文档最多两段 |
| answer/sources/confidence 结构化输出 | 通过 | Pydantic 严格模型；真实接口返回三字段；无证据 confidence=0 |
| 明确/模糊/未知问题及质量/幻觉观察 | 功能与评测通过；旧冒烟需修复 | 三类真实 HTTP 请求已测，310 题完整重跑；低分属于效果问题，不凭空附加题目未要求的质量达标线 |
| Task 1：LLM Planner、Schema、Agent allow-list、稳定性 | 实现并真实实测通过 | API 使用 Ollama 返回计划；相同任务 10/10 有效，详见原始记录。默认报告仍使用固定模拟器 |
| Task 2：ReAct 三工具、自主继续/结束、与 Fixed 对比 | 实现；真实效果有缺口 | Demo 对比可复现；真实 EKS 查询选取无效文档参数后退出，没有利用可用 Search 证据 |
| Task 3：Diagnosis/Critic/Feedback，最多两次重试，逐轮记录 | 实现并真实实测通过流程 | 真实调用完成三轮，retries=2；最终 passed=false，不能声称第二轮已修复问题 |
| Task 4：Single 与 Supervisor/Specialists、五类指标与结论 | 部分完成 | 两版与指标存在；Supervisor 未执行生成计划，Answer Quality 的计算掩盖正文无答案；原报告不是真实模型比较 |
| 回答“Multi-Agent 是否一定更好” | 通过 | README 与报告明确回答“不一定”，并解释协调开销与适用情形 |

本次完整 TechQA 评测使用当前默认 Agent Top-8；独立检索指标计算 Top-10。README 的历史表注明 Top-10，因此拒答准确率和延迟不要求与历史表完全相同。本次 150 条不可回答问题中仅 59 条正确拒答，另外 91 条仍返回了来源；有来源或严格 JSON 并不保证问题可被正确回答。原始逐题响应已保存为 `evidence/techqa-core/runs.json`。

## 6. 应优先处理的问题

### 1）Ingestion 在 Embedding 全部失败时仍报告进程成功

- 位置：`src/rag/ingestion/cli.py:94`、`src/rag/ingestion/pipeline.py:105`。
- 复现：`python main.py data/sample --summary-provider extractive --embedding-provider ollama --qdrant-path <新的审计目录>`。
- 结果：`/api/embed` 返回 404，无向量成功写入；进程退出码仍为 0。CLI 只检查“是否解析成功过文件”，没有检查 Embedding/建库/写入失败。
- 影响：CI、批处理或提交演示会把失败误报为成功。需要统计处理阶段失败，并区分全部已存在的成功幂等运行与未成功写入的失败运行。
- 证据：`missing-embedding.log`。

### 2）Reranker 降级后，相关性阈值与分数空间不匹配

- 位置：`src/rag/generation/service.py:72`，结合 `src/rag/retrieval/pipeline.py` 的降级分支。
- 同一 S3 查询，正常精排最高分 0.6254，回答成功；模拟重排超时后仍有 5 个候选，但最高 RRF 分数仅 0.0320，被精排阈值 0.545 全部过滤，返回 `below_relevance_threshold`。
- 影响：检索层的降级单测通过，完整 API 却无法按原候选继续回答。需要为原始 Dense/RRF 分数分别校准阈值，或采用不依赖精排分数的降级准入方式。
- 证据：`edge-results.json`。

### 3）Agent 对比报告的满分不能证明最终答案质量

- 位置：`agentic-rag-homework/evaluation/run.py:20`。
- 评分把 `answer` 与全部 `sources.quote` 拼接。四条可回答问题的 Multi-Agent 正文均为 “Use the retrieved checks and retain the citation for verification. [evidence]”，没有回答 Lambda 范围、S3 策略、SSH 或 EKS 排查事实，却因来源包含关键词取得满分。
- 用相同关键词规则仅检查最终答案正文，四条可回答题均为 0，连同一条正确拒答的五题平均为 0.20；原表为 1.00。这是额外诊断指标，不应冒充新的人工答案质量标准。
- `evaluation.run` 调用 `build_advanced()` 时没有传入环境模型，因此即使设置 `MODEL_PROVIDER=ollama`，该评测入口仍使用 DemoStructuredModel。API 的模型切换则确实有效。
- 建议分别评价答案完整性、证据支持和拒答；让评测入口显式选择模型、记录模型配置并容纳逐题失败，再重做 Fixed/ReAct 与 Single/Multi 对比。
- 证据：`agentic-demo/runs.json`、`homework-demo-http.json`、`homework-ollama-http.json`。

### 4）Multi-Agent 的 LLM 计划没有驱动执行

- 位置：`agentic-rag-homework/agents/systems.py:45`。
- 计划生成后固定执行 Research，再视来源情况执行 CriticLoop；没有按 `plan.tasks` 的 agent/objective/dependencies 调度。`data_analyst`、`report_writer` 在允许名称和计划里出现，但没有对应执行分派。
- 这不否定 Planner 本身已经由 LLM 生成，但现有 Supervisor 仍是固定工作流，计划是返回记录而不是实际执行依据。
- 建议实现 Agent 注册表、按依赖执行、向每步传入任务目标与前置产物，并检查 Planner 只能选择可执行 Agent。

### 5）统一测试入口与干净环境复现失败

- 根目录 `pyproject.toml:48` 的 `testpaths = ["tests", "."]` 把子项目测试收集进来，引发 `api`、`agents`、`evaluation` 导入错误。应明确隔离三个项目的测试入口。
- `enterprise-ai-agent/tests/test_agent_evaluation.py:15` 直接读取 Git 忽略的官方 dev 文件。没有下载数据的源码副本复现为 **1 failed、33 passed**，与 README “单元测试使用 fixture，不下载/索引全量数据”的说法不一致。
- `enterprise-ai-agent/evaluation/smoke_api.py:33` 对 WebSphere 问题断言答案含 `900`；在当前官方 TechQA 库上失败。应换成与当前文档对应、验证事实而非旧字符串的冒烟案例。
- 证据：`enterprise-clean-pytest.log`、`enterprise-original-smoke.log`。

### 6）真实模型与当前环境的边界

- Ollama 服务在线，只有 `llama3.2:3b`；默认 `nomic-embed-text` 缺失，因此默认语义 Embedding 流程不能运行。
- `sentence-transformers` 未安装，CrossEncoder 未做真实模型验收；当前通过的是词法重排与 CrossEncoder 的注入式测试。
- 全量 TechQA Qdrant 服务未运行，README 中百万级全量点数无法在本次确认。当前实际验证的是本地 core 库的 117,580 个点。
- 真实 ReAct 的 EKS 案例把 `EKS CrashLoopBackOff` 当作文档 ID，得到空结果后停止。建议把可读取文档 ID 作为工具参数的有效集合，并把失败观察反馈给决策器，允许转用 Search。
- 真实 Critic 对正确的 Lambda 范围也给出不合适批评，最终两次重试后仍失败。流程边界正确，但反映了模型/Prompt 效果不足。
- 根 API 的 S3 答案提到 “Bucket policy / Object-level policy”，而实际 S1 Chunk 只有显式/隐式拒绝解释和请求信息记录，没有这两条策略清单。这说明引用 ID 存在并不能证明事实受引用支持；本次确实观察到无依据扩展。
- 根项目 `.env.example` 和 YAML 提供了配置说明，但运行时读取的是进程环境变量，未发现自动加载 `.env` 或 YAML 的代码；只复制 `.env` 并修改它不会自动生效。

### 7）GitHub 提交物尚不能验收

- 当前 `git status`：`agentic-rag-homework/`、`enterprise-ai-agent/` 为未跟踪目录；`tests/test_ingestion_ocr.py` 也未跟踪。README、OCR 解析逻辑和检索结果文件还有未提交修改。
- 本地三个阶段 Tag 均存在，并已测试它们的独立源码快照。`retriever-v3-hybrid` 位于 `b5e2949`，当前 HEAD 为后续的 `38c9597`，Tag 不包含其后的全部完善项。
- origin 配置为 `https://github.com/BoiledFishz/RAG-Ingestion-Pipeline.git`。本次 GitHub 远端查询因代理/TLS/访问问题未成功，因此不能确认远端分支、标签和最新文件的状态。
- 作业交付前，需要提交应交文件、验证干净 clone 的安装与测试，再确认 GitHub 分支和三个 Tag 可访问。不能仅凭本地目录存在判定交付完成。

### 8）context_summary 的字符截断破坏“一句话”要求

- 位置：`src/rag/ingestion/providers.py` 的 `_first_sentence()`。
- 该函数在提取首句后再次执行 `value[:max_chars]`，没有保留完整单词或句尾。
- 本次实际入库的真实 LLM 摘要长度为 240 字符，末尾是 `recording relevant informati`，单词和句子都被截断；它虽然来自 LLM 且非 fallback，仍不能按严格要求认定为“一句完整的 context_summary”。
- 应在 Prompt 中限制长度，并对超长结果重新摘要或使用保留完整句子的处理；新增真实边界样例防止再次出现。
- 证据：`llm-summary-ingestion.json`。

## 7. 建议验收顺序

1. 修正主流水线的失败退出码、摘要截断、测试收集范围、Enterprise 的数据依赖测试与旧冒烟断言。
2. 修正 Reranker 降级阈值；增加从重排失败一直验证到 API 响应的回归用例。
3. 让 Agent 的计划驱动执行，修正答案质量指标和模型选择入口；保留真实失败样例后重跑对比。
4. 准备默认模型与数据库依赖，重新验证完整语义 Embedding → 检索 → LLM 路径；单独说明 Hash/模拟路径的用途。
5. 提交文件，检查干净克隆、README 命令和远端标签，最后形成可提交的仓库链接。

这些步骤中，低分本身不等于“未实现作业”：原题没有指定必须达到的准确率。真正需要补齐的是可复现运行、可信的评测、实际执行逻辑和交付状态。本次仅做审计与隔离验证，没有修改上述业务实现。

## 8. 原始证据

轻量结果保存在本报告旁的 [evidence/](evidence/)：HTTP 请求与响应、OCR/幂等日志、评分结果、真实 Planner 10 次记录、干净源码失败日志及 Tag 测试结果。完整中间目录为仓库根目录下的 `.test_tmp/audit-2026-09-29/`；Qdrant 测试数据库与 Tag 源码快照保留在那里，不作为提交文件。
