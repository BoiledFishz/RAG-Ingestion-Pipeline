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
