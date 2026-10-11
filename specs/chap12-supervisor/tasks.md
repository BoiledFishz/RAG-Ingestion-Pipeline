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
