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
