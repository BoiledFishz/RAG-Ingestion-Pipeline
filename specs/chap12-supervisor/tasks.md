# Tasks 与验收证据

| 任务 | 实现 | 自动化测试 |
| --- | --- | --- |
| 随机样本与索引 | `agents/chap12/sample.py`、`evaluation/chap12_build_sample.py` | `tests/chap12/test_sample.py` |
| Contract / State | `agents/chap12/contracts.py` | 各测试文件 |
| DB Worker：计数正确、时间范围、零值、截断、注入、越权、只读、语句超时、有界重试、预算 | `agents/chap12/db_worker.py` | `test_db_worker.py`（与原始 JSON 独立复算对比） |
| RAG Worker：状态映射、引用、超时、依赖失败、LLM 预算、拒权零调用 | `agents/chap12/rag_worker.py` | `test_rag_worker.py` |
| Supervisor：36 种状态组合、路由、未注册 Worker、输入隔离、全局拒权、截止时间取消、并行、Worker 崩溃 | `agents/chap12/supervisor.py`、`planner.py` | `test_supervisor.py` |
| API：服务端凭证、正文不能授权、未知 goal/字段 | `api/chap12_main.py` | `test_api.py` |
| 真实组件端到端（官方 fixture 文档，offline profile） | `agents/chap12/factory.py`、`tools/sample_retriever.py` | `test_e2e_offline.py` |
| 单 Agent vs Multi-Agent 对照 | `evaluation/chap12_compare.py` | `evaluation/chap12/results/offline_20261011/`（v1）、`offline_v2_20261011/`（v2） |
| 样本范围 dense + MiniLM 重排、调参集阈值 | `agents/chap12/dense.py`、`evaluation/chap12_build_dense.py`、`evaluation/chap12_retrieval_tune.py` | `test_dense.py`；`evaluation/chap12/tune/` |
| 产品推断与澄清语义 | `db_worker.py`、`planner.py` | `test_db_worker.py` 中的推断、权限和澄清用例 |

## 工作单执行记录（2026-10-11 20:05 之后）

每条记录包括：改动内容、运行过的命令、实际结果。

### W0 工作区隔离
- 改动：主工作区切回原分支 `codex/project2-course-completion`，旧 project2 的未提交改动原样保留在主工作区；为 `feature/chap12-supervisor-lite` 新建 worktree `.worktrees/chap12`，并把 `.worktrees/` 加入 `.git/info/exclude`。worktree 中的 `.rag_data/` 只有指向主目录数据的符号链接（被 gitignore）。
- 命令：`git worktree add .worktrees/chap12 feature/chap12-supervisor-lite`（首次因 180 s 超时中断，之后用 `git checkout -f ab4e8d7 -- <dir>` 分批补齐）；`git status --short` → 只剩 1 个未跟踪文件 REVIEW_PACKAGE.md。
- 结果：在干净的 worktree 中运行 `pytest tests/chap12 -q` → `91 passed`。

### P0-1 流程补齐（文档部分）
- 改动：新增 review_log.md、contract_changelog.md、plan.md（事后补写）、analyze_report.md；纳入 REVIEW_PACKAGE.md。
- 命令：`uvx --from git+https://github.com/github/spec-kit.git specify version` → `CLI Version 1.1.4.dev0`；`specify --help` → 子命令中没有 analyze/checklist。
- 结果：analyze 由 Claude 按模板执行，发现 13 项问题，其中 2 项 CRITICAL（RAG 未按授权过滤；没有 constitution）。

### P0-2 权限边界核查与修复
- 核查结论（修复前）：RAG 检索**不**受 TrustedContext 约束，任何主体都可能在引用中看到未授权产品的文档。DB 推断在全部文档上进行，推断出的未授权产品会以 permission_denied 返回；当时的错误信息是通用文案、没有 payload，响应中不含产品名，但“拒权”这一状态本身会暗示问题与某个未授权产品相关。
- 改动：新增 `agents/chap12/scope.py`（ContextVar、DocumentScope、ScopedRetriever）；`tools/sample_retriever.py` 的两路检索都经过范围过滤，父文档展开前再检查一次；`rag_worker.py` 设置范围并追加 limitation；`db_worker.py` 的推断只考虑授权文档；新增 `tests/chap12/test_scope.py`（4 项），调整 `test_db_worker.py` 中一项的预期。
- 命令：`pytest tests/chap12 -q` → `95 passed`；`ruff check` → 通过。
- 结果：受限主体（只授权 SSFKSJ）查询 Streams 问题时，引用与检索候选中没有 SSCRJU 文档，DB 返回 permission_denied，序列化后的响应中不含 SSCRJU 和这两篇 doc_id；未写明产品的问题在受限时不会推断出 Streams。

### P0-3 截止时间取消的真实性
- 核查结论（修复前）：RAGAgent 和 LLM 调用是原生 async（httpx，可取消）；BM25 和父文档查询（Project 1 `FullSparseRetriever`/`TechQAParentResolver`）、MiniLM 编码、DB 推断与查询都在 `asyncio.to_thread` 中执行。协程被取消后线程仍会继续；其中 RAG 的 BM25 SQL 和 DB 推断里的 `index.search` 没有任何截止检查，可能在截止后继续发出 SQL。
- 改动：新增 `agents/chap12/metered.py`（MeteredConnection、MeteredIndex、CountingReranker）；`budget.py` 增加 `sql`、`local` 两个类别和 `deadline_remaining`；DB Worker 的连接改为逐语句计量，推断和查询中的 `BudgetExhausted(deadline)` 映射为 timeout；dense 检索和重排在编码前计量 `local`；Contract 升级为 chap12-v2；新增 `tests/chap12/test_deadline.py`（3 项，用线程内真实的 `time.sleep` 阻塞）。
- 命令：`pytest tests/chap12 -q` → `98 passed`；`ruff check ...` → `All checks passed!`；`mypy --python-version 3.12 agents/chap12 ...` → `Success: no issues found in 18 source files`。
- 结果：DB 线程在截止后醒来时，第一条 SQL 就被 `BudgetExhausted(deadline)` 拒绝；返回后再等 1.2 s，预算计数没有任何变化，sql 为 0。RAG 检索线程阻塞到截止之后，也没有再产生任何计数。

### P2（第一部分）count=0 语义、重试上限、预算细化测试
- 改动：`db_worker.py` 按 D1 修改状态判定；`test_db_worker.py` 中的零值用例改为同时断言三种操作；`test_rag_worker.py` 新增“证据校验重试达到上限”用例（真实的 Project 1 RAGAgent + 总是失败的 selector，断言调用 2 次、状态 failed、错误类别 invalid_evidence、错误文案 “evidence validation failed after retry”）；新增 `test_metering.py`（逐语句 SQL 按 Worker 计数、SQL 上限阻断下一条语句、embedding 未命中与缓存命中分开计数）。
- 命令：`pytest tests/chap12 -q` → `102 passed`；`ruff check` → 通过。

### P1-3 拒答信号（调参集）
- 改动：新增 `evaluation/chap12_refusal_signals.py`，输出 `tune/refusal_signals.json`（含 top-1 分数的完整阈值曲线）；`tools/sample_retriever.py` 加入 `refusal_gate()`（只在 MiniLM 重排下生效，可用环境变量关闭）；`test_dense.py` 新增门槛用例。
- 命令：`python -m evaluation.chap12_refusal_signals` → 结果见 spec §9（只有 top-1/top-2 间隔的 BA 为 0.614，按事先规则采用，其余 ≤ 0.571）；`pytest tests/chap12 -q` → `103 passed`。

### P1-5 产品槽位先行的替代方案（调参集）
- 改动：新增 `evaluation/chap12_product_filter_study.py`，输出 `tune/product_filter_study.json`；spec §10 写入比较结果与结论。
- 命令：`python -m evaluation.chap12_product_filter_study` → 当前方案 R@8 0.688、MRR 0.535，替代方案 R@8 0.661、MRR 0.508，槽位解析额外 124 ms → 保留当前方案。

### P1-5（续）数据部分服务于回答；P0-4（第一部分）token 采集
- 改动：`planner.py` 中 explain_and_data 的默认操作改为 list_recent_documents；`supervisor.py` 把列表渲染为“[相关文档]”；新增 `agents/chap12/ollama_tokens.py`（TokenMeteredOllamaModel 继承 Project 1 的适配器，重复相同的请求并记录 prompt_eval_count/eval_count），`factory.py` 的 ollama 档位改用它；`budget.py` 增加 `record_tokens`；Usage 增加 token 字段；新增 `test_ollama_tokens.py`（用 httpx MockTransport 验证请求参数与 Project 1 一致、token 累加、缺失时为 null、遇到 length 截断时失败）；更新 e2e 测试。
- 命令：`pytest tests/chap12 -q` → `105 passed`；`ruff check` → 通过。
- 未执行：真实 Ollama 的 token 采集（本环境连不到 Ollama）。

### P1-1 / P1-2 / P1-4（准备）混合任务集、指标、确认集
- 改动：
  - `evaluation/chap12_build_tasks.py`：构建混合任务集。explain 76、explain_and_data 74（评测集问题按 Y/N 分层后交替分配）；data 60（3 种模板，金标从原始 metadata JSON 独立复算，分类规则也是独立重新实现的）。
  - `evaluation/chap12_eval.py`：三个系统（p1_single = Project 1 原配置，single，multi）；按任务类型报告正确完成率、整体完成率、BA、R@k/MRR、数据正确率、产品一致率、相关文档是否含金标、延迟和各类调用计数；支持多次重复，CI 用按任务的 bootstrap；可传入运行元数据。
  - `evaluation/chap12_failed_decomposition.py`：拆分 v1→v2 的 failed 变化。
  - `chap12_build_sample.py` 的 `--exclude-manifest` 改为可以接收多个文件。
  - 构建确认集（种子 20261013，排除评测集和调参集，113 Y / 37 N，6,520 篇文档）及其 dense 附属文件。
  - `factory.build_rag_agent` 支持注入检索器。
- 命令与结果：
  - `python -m evaluation.chap12_build_tasks --split sample --seed 20261021` → explain 76 / explain_and_data 74 / data 60；confirm 使用种子 20261023，数量相同。
  - `python -m evaluation.chap12_failed_decomposition` → v1 的 44 个 failed 中，33 个由产品推断补救（数据完成），11 个是重新归类（failed→no_data）。
  - `AGENT_PROFILE=offline python -m evaluation.chap12_eval --split sample --output evaluation/results/chap12/offline_v3_sample` → 630 条记录，摘要写入 comparison.md。
  - `pytest tests/chap12 -q` → `105 passed`；`ruff` 通过；`mypy --python-version 3.12`（20 个文件）→ `Success`。
- 冻结：本提交即确认集运行所用的配置，确认集只运行一次。

### P0-4 真实模型评测脚本
- 改动：
  - 新增 `evaluation/chap12_compare_real.ps1`（Windows / .venv312）和 `.sh`（Linux/macOS）。脚本依次：检查 Ollama；缺少模型时自动 pull；记录 Ollama 版本与两个模型的 digest、git commit 和配置，写入 meta.json；只在调参集上标定 nomic 阈值并做拒答信号研究；在评测集上按 `-Repeats 3`、`-LimitPerType 30`（按类型取随机前缀，即分层子集；0 表示全部）运行三个系统；`-Confirm` 时对确认集运行一次，并拒绝第二次。
  - `chap12_retrieval_tune.py`、`chap12_refusal_signals.py` 增加 `--rerank nomic`（阈值合并写入 thresholds.json，信号写入 refusal_signals_nomic.json）。
  - `sample_retriever.py`：阈值和间隔门槛按重排器分别读取；p1_single 使用 `use_calibration=False`，保证它始终是 Project 1 原阈值。
  - `chap12_eval.py`：每道题、每次重复都轮换系统执行顺序，避免缓存预热只让某一个系统受益。
- 继续沿用 0.6555 还是重新标定：**重新标定**。0.6555 是在全库 hybrid + nomic、training split 上标定的，而现在的范围是样本库，分数分布不同。脚本只在调参集上重新标定；标定之前，如果 thresholds.json 中没有 nomic 键，就回退到 0.6555。
- 命令与结果：
  - `bash -n evaluation/chap12_compare_real.sh` → 语法通过。
  - **管线连通性测试（mock，不是模型结果）**：在本机起了一个返回固定 JSON 的假 Ollama HTTP 服务，用 `LIMIT_PER_TYPE=1 REPEATS=1` 完整跑通 .sh：meta.json 记录了 mock digest；token 被采集到（例如 single：prompt 300 / completion 6）；embedding 的未命中和命中分别计数。测试结束后，已把 thresholds.json 恢复原样，并删除由 mock 产生的 nomic 标定文件、结果目录和 rerank 缓存，这些都没有提交。
  - `.ps1`：本环境没有 PowerShell，**语法和运行都未验证**。
- 未执行：真实 Ollama 运行（本环境连不到 Ollama）。comparison.md 中真实档位的表格全部标为“未执行”。

### P2（第二部分）Python 3.11 与 uvicorn 冒烟测试
- Python 3.11：使用 `uv python install 3.11`，得到 CPython 3.11.17。
  - `pytest tests -q --ignore=tests/project2` → `157 passed`（105 个 chap12 测试 + 52 个已有测试）。
  - `mypy agents/chap12 api/chap12_main.py tools/sample_retriever.py`（使用 pyproject 的 3.11 配置）→ `Success: no issues found in 15 source files`。此前“numpy 存根在 3.11 下报语法错误”的问题，在这个只装最小依赖的环境中没有复现。
  - 3.11 环境没有装 torch（离线安装包只有 cp312 的 torch），因此依赖真实 MiniLM 的评测脚本只在 3.12 下运行过。
- uvicorn 冒烟测试：输出原样保存在 `evaluation/results/chap12/uvicorn_smoke.txt`。`/healthz` 返回 200；无凭证返回 401；full 凭证返回 200，状态 partial（RAG 因间隔门槛拒答，DB 正常完成）；无权限凭证返回 200，状态 permission_denied，tool_calls 为 0；只授权 SSFKSJ 的凭证返回 permission_denied，引用为空，响应中不含 SSCRJU；在请求正文里带权限字段返回 422。
- 设计说明：权限拒绝通过响应体中的 `status=permission_denied` 表达，HTTP 状态码为 200；凭证缺失或无效时返回 401。

## 2026-10-17 剩余事项（用户要求“把 13 项都完成”）

规则不变：阈值与参数只在调参集（20261012）上选；评测集（20261011）只用于报告；确认集（20261013）只运行一次；不改 Project 1 代码。
新增调参集混合任务：`python -m evaluation.chap12_build_tasks --split tune --seed 20261022` → explain 75 / explain_and_data 75 / data 60（种子 20261022 此前未使用）。

### 第 7、8 项 相关文档改为产品内相关性排序；模型选择产品 + 程序校验
- 研究（只用调参集）：`python -m evaluation.chap12_product_study` → `evaluation/chap12/tune/product_study.json`。
  - 产品解析：explain_and_data 75 题中，字面命中 32、BM25 推断 32、无法确定 11；Y 题解析率 0.875（49/56），解析出的产品与金标文档一致 0.694（34/49）。
  - 相关文档含金标（已解析的 49 道 Y 题）：最近文档 0.082（4/49）；产品内 BM25 0.469（23/49）。→ 采用产品内 BM25。
  - 候选覆盖（模型选择的上限，不是准确率）：未解析的 7 题，前 5/10/20 篇文档的产品覆盖金标 5/7；解析错误的 15 题，覆盖 9/11/12。→ 候选取前 10 篇、最多 8 个产品。
- 改动：`contracts.py`（chap12-v3，新操作 `search_product_documents`、来源 `model_pick`）；`db_worker.py`（新模板，IN 列表只含占位符，产品过滤始终生效；`_resolve` 按 fallback/first 顺序调用规则与模型；`_candidates` 只在授权文档中取候选）；新增 `product_pick.py`（模型只返回编号，非整数、越界、0、异常都视为未选）；`planner.py`、`supervisor.py`、`factory.py`（仅 ollama 档位创建选择器）；`chap12_eval.py`（新操作的独立校验：行不重复且全部属于该产品并满足过滤条件；相关文档指标覆盖两种列表操作）；`chap12_product_study.py`（`--pick` 用真实模型在调参集上比较两种顺序，事先规则：first 的命中率须比 fallback 高至少 0.05 才采用 first）。
- 测试：新增 `tests/chap12/test_product_pick.py`（13 个测试函数、21 个用例：相关文档只含本产品且受过滤约束、问题文本不会进入 SQL、缺问题时 invalid_input、合法选择被采用并计入 llm 预算、8 种非法回复回退规则、无规则时要求澄清、fallback 模式只在规则失败时调用模型、off 模式不调用、未授权产品不会出现在候选中、显式产品不调用模型、环境变量覆盖）；更新 e2e 断言。
- 命令与结果：`pytest tests/chap12 -q` → `126 passed`；`ruff check agents/chap12 evaluation/chap12_product_study.py evaluation/chap12_eval.py tests/chap12` → `All checks passed!`；`MYPYPATH=../src mypy --python-version 3.12 agents/chap12 api/chap12_main.py tools/sample_retriever.py evaluation/chap12_product_study.py evaluation/chap12_eval.py` → 本次涉及的文件无错误（仅报告 Project 1 `src/rag/techqa` 中 2 个既有问题，未修改）。
- 未执行：`--pick` 真实模型研究（需要 Ollama，放在 Windows 运行步骤中）；评测集上的效果（等真实模型评测一并报告）。
- 影响说明：确认集此前的离线运行（offline_v3_confirm_once）使用的是旧配置，不再代表当前配置；按“只运行一次”的规则不再离线重跑确认集，当前配置的确认结果以之后唯一一次真实模型确认运行为准。

### 第 9 项 检索调参（只用调参集）
- 事先登记：先提交 `evaluation/chap12_retrieval_sweep.py`（提交 408e56d），其中写明网格与采用规则，之后才运行。网格：重排权重（语义、词项覆盖、BM25 先验）5 组 × 候选深度（candidate_k、rerank_k）2 组，共 10 个变体。规则：取 R@8 最高者；只有 R@8 ≥ 当前 + 0.03 且 MRR ≥ 当前 − 0.01 才采用。
- 命令：`python -m evaluation.chap12_retrieval_sweep`（分两次运行，可断点续跑）→ `evaluation/chap12/tune/retrieval_sweep.json`。
- 结果（调参集，112 道 Y 题，离线 MiniLM 重排）：当前配置 R@8 0.688、MRR 0.546（与此前报告一致）；最好的变体 w=0.6/0.2/0.2、k=30/20 为 R@8 0.714、MRR 0.550，只多 3 题（+0.026），未达到 +0.03 → **不采用，配置不变**。其余变体 R@8 在 0.661–0.705 之间。
- 结论：在这个网格内，调重排权重或加深候选都改善不了检索；R@20 只有 0.777–0.839，瓶颈在候选召回本身，不在排序。没有再追加未登记的变体。

### 第 10 项 Critic 与一次有界 Replan
- 设计：`agents/chap12/critic.py` 是确定性的程序检查，不调用模型。C1 检查已发布回答的引用（有引用、有引文、在检索集合内）；C2 检查数据部分的产品是否属于回答所引用文档的产品。只有 C2 会触发 Replan，并且只在产品不是用户给定的情况下（来源为 inferred 或 model_pick，或者无法确定产品）：用引用文档的产品（来源 `rag_citation`）重新运行一次 DB Worker。每个请求最多 1 次；仍经过授权、预算和截止时间检查；只有重新查询结果为 completed/partial 时才替换原结果，否则保留原结果并写入限制说明。用户给定的产品只提示、不替换。`CHAP12_CRITIC=off` 可关闭。
- 测试：新增 `tests/chap12/test_critic.py`（10 个用例：推断产品冲突时 Replan；显式或字面产品只提示不替换；无法确定时取引用文档的产品；一致或无引用时不动作；引用不在检索集合内时报告；集成测试中真实 DB Worker 恰好被调用 2 次且结果被替换；关闭时不 Replan；未授权产品不会被用于 Replan；预算不足时保留原结果并说明）。
- 命令：`pytest tests/chap12 -q` → `136 passed`。
- 事先登记的默认值规则（在调参集运行之前写下）：在调参集的 explain_and_data 任务上，用离线 multi 系统分别以 Critic 开、关各运行一次；只有“产品与金标文档一致率”（Y 题）提高至少 0.05，并且 data_correct 和 explain_and_data 的正确完成率都没有降低，默认才设为开；否则默认关。
- 调参集运行（离线，multi，explain_and_data 75 题，各 1 次）：
  - `AGENT_PROFILE=offline CHAP12_CRITIC=on python -m evaluation.chap12_eval --split tune --systems multi --types explain_and_data --output evaluation/results/chap12/tune_critic_on`
  - 同上，`CHAP12_CRITIC=off`，输出 `tune_critic_off`。
  - 结果（开 / 关）：产品与金标文档一致率 0.6863 / 0.6939；data_correct 0.8933 / 0.8533；正确完成率 0.3333 / 0.3200；相关文档含金标 0.4706 / 0.4694；Replan 率 0.04 / 0（75 题中 3 题触发）。
  - 按事先规则，产品一致率没有提高 0.05（反而低 0.008）→ **默认关闭**（`CHAP12_CRITIC` 默认 off，设为 on 可开启）。data_correct 虽然高了 0.04（Replan 补上了无法确定产品的题），但它不是登记的主指标，不据此改判。
  - Replan 很少触发的原因：离线档位下回答本身引用的文档少，且多数情况下引用文档的产品与推断产品一致。
- 测试更新：Critic 相关集成测试显式开启；新增“默认关闭”用例。`pytest tests/chap12 -q` → `137 passed`；ruff 通过。

### 第 13 项 索引重建与内容校验；新建确认集 confirm2
- 改动：新增 `evaluation/chap12_rebuild_indices.py`。`--record` 记录每个切分索引与 dense 附属文件的内容摘要（逐表、按全部列排序后对每一行做 SHA-256；不比较文件字节，因为 SQLite 的页面布局可能不同），写入 `evaluation/chap12/index_digests.json`；`--check` 只校验现有文件；`--rebuild` 用原命令和原种子在临时目录重建，比较摘要以及重新生成的 tasks.jsonl/gold.jsonl 与已提交文件是否逐字节相同，`--install` 在全部一致时才把索引复制进 `.rag_data`。
- 新建 confirm2：`python -m evaluation.chap12_build_sample --seed 20261014 --index ../.rag_data/chap12_confirm2.sqlite --output evaluation/chap12/confirm2 --exclude-manifest evaluation/chap12/sample_manifest.json evaluation/chap12/tune/sample_manifest.json evaluation/chap12/confirm/sample_manifest.json` → 150 题（102 Y / 48 N），6,702 篇文档，无缺失；`chap12_build_dense` → 29,501 个块；`chap12_build_tasks --split confirm2 --seed 20261024` → explain 75 / explain_and_data 75 / data 60。原因：v3 改动发生在原确认集运行之后（见 spec §12.5）。confirm2 尚未运行任何系统。
- 命令与结果：
  - `python -m evaluation.chap12_rebuild_indices --record`（四个切分）→ 摘要已写入。
  - `python -m evaluation.chap12_rebuild_indices --rebuild --workdir <临时目录>` → sample、tune、confirm 三个切分的索引、dense、tasks.jsonl、gold.jsonl **全部一致**；confirm2 建好后单独 `--splits confirm2` 重建，同样一致。合并后的输出见 `evaluation/results/chap12/rebuild_verify_20261017.json`。每个切分重建约 30 秒（Linux VM，读取主检出中的全量索引）。
  - `pytest tests/chap12 -q` → `137 passed`；ruff 通过。
- 未执行：Windows 上的重建（脚本相同；只在 Linux VM 上运行过）。

### 第 11 项 Spec Kit 初始化与 constitution 草案
- 命令：`uvx --from git+https://github.com/github/spec-kit.git@v1.2.1 specify init --here --force --integration claude --script ps --non-interactive --ignore-agent-tools`（在空目录中执行，再把生成的 `.specify/` 与 `.claude/skills/speckit-*` 复制到仓库根目录；没有覆盖任何已有文件）。版本固定为发布标签 v1.2.1。
- 改动：`.specify/memory/constitution.md` 写成草案 1.0.0-draft，共 7 条原则（证据先于结论、切分纪律、复用不修改、程序掌握权限、有界执行、版本化 Contract、可复现产物）以及流程与治理。**状态为未批准**，批准日期留作 TODO，须由人工批准。文中注明它写于实现之后。
- `analyze_report.md` 追加 Constitution Alignment 一节（Claude 按 speckit-analyze 模板执行，不是 CLI 输出）：K1“实现先于 Spec、无事前人工审阅”为 CRITICAL，无法事后补救，如实披露；K2 确认集已用，以 confirm2 处理；其余原则符合。核对 K5 的命令：`git diff --name-only 38f8483 HEAD` 只列出 chap12 相关文件（38f8483 为本分支起点）。

### 第 5 项 人工审阅（只能由人完成）
- 改动：新增 `spec_review_checklist.md`，按 A–G 七组共 22 项，供审阅者逐条勾选、签名。spec.md 新增 §12（v3 改动）并在开头注明“实现后补写、未经人工审阅”。
- 未执行：人工审阅本身。原因：必须由人完成，Claude 不代填。

### 第 12 项 worktree 在 Linux VM 与 Windows 之间共用
- 现象：worktree 的 `.git` 文件写的是 VM 的绝对路径（/sessions/...），Windows 上的 git 找不到。此前建议的 `git worktree prune` **是错误建议**：在 Windows 上运行它会把这个 worktree 的元数据当作失效而删除，不能运行。
- 改动（不进入提交，属于本地 git 元数据）：`.worktrees/chap12/.git` 改为相对路径 `gitdir: ../../.git/worktrees/chap12`（git 一直支持相对路径，两边都能用）；对该 worktree 执行等价于 `git worktree lock` 的操作（写入 `.git/worktrees/chap12/locked` 并注明原因），防止被 prune。没有使用 `worktree.useRelativePaths`，因为 VM 中的 git 2.34 不认识这个扩展，会导致整个仓库无法打开。
- 命令与结果：VM 中 `git status`、`git log` 正常；`git worktree list` 显示该 worktree 为 locked。Windows 端的验证见下面 Windows 运行记录中的 probe 步骤。

### 第 1–4 项 Windows 运行脚本
- `chap12_compare_real.ps1`：自动寻找本检出或主检出的 `.venv312`；worktree 中没有索引时，建立指向主检出 `.rag_data` 的目录联接；运行前用 `chap12_rebuild_indices --check` 校验索引内容；调参集步骤增加模型选择产品顺序的研究；`-TuneOnly` 只做调参集决策；正式运行前要求调参输出已提交（配置冻结）；确认运行改用 confirm2，任何已存在的 confirm2 运行都会让脚本拒绝再跑。`.sh` 同步修改，`bash -n` 通过。
- 本地启动器 `.chap12_run/run_all.cmd`（不提交，已加入 .git/info/exclude）：依次 probe → push 两个分支 → 用 gh 建 PR（目标分支 codex/project2-course-completion，用户 2026-10-17 选择）→ 调参集决策并提交 → 评测集 3 次重复、每类 30 题 → confirm2 一次 → 提交结果并 push。日志写入 `.chap12_run/run_all.log`。由用户本人双击运行（Claude 对资源管理器只有点击权限，不通过它执行命令）。

### 当前配置（v3 契约，2026-10-17）在评测集上的离线运行（只用于报告）
- 命令：`AGENT_PROFILE=offline python -m evaluation.chap12_eval --split sample --output evaluation/results/chap12/offline_v4_sample --resume`（Linux VM，索引在本地磁盘）→ 630 条记录。
- 与 `offline_v3_sample_rotated` 相比：Multi-Agent 的 explain_and_data 中“相关文档含金标”由 0.074 升到 0.4815；正确完成率（0.3514）、数据正确率（0.8919）、产品一致率（0.7037）、explain 与 data 的全部指标不变（离线档位不调用模型选择产品，Critic 默认关闭）。
- 延迟不可与 v3 直接比较：v3 运行时索引在 Windows 挂载目录上，本次在 VM 本地磁盘上。
