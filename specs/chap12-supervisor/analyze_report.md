# Specification Analysis Report（按 Spec Kit analyze 模板执行）

- 执行方式：Claude 按 Spec Kit 1.1.4.dev0 的 `core_pack/commands/analyze.md` 模板，对 spec.md、plan.md、tasks.md 做只读分析，分析期间没有修改这三个文件。**这不是 CLI 输出**：analyze 本身就是交给代理执行的提示词命令。
- 执行时间：2026-10-11 20:05 之后（PT），在本轮任何代码改动之前；对象为提交 ab4e8d7 的文档，加上当时刚补写的 plan.md。
- 前置检查：模板要求的 `check-prerequisites` 脚本无法运行，因为仓库没有 `.specify/`。plan.md 是事后补写的。没有 constitution，所以 D 类（Constitution Alignment）无法检查。
- spec.md 中没有 FR-/SC- 编号，下表的需求键由各章节推导，例如 `spec§5-db-scope`。

| ID | 类别 | 严重度 | 位置 | 发现 | 建议 |
| --- | --- | --- | --- | --- | --- |
| G1 | Coverage Gap | CRITICAL | spec §5；agents/chap12 | spec §5 写明 DB 查询受授权产品约束，但 RAG 检索不受 TrustedContext 约束，未授权产品的文档可能出现在引用中。没有任务、也没有测试覆盖这一点 | 按 D3 在检索时过滤，并补测试（P0-2） |
| D1 | Constitution | CRITICAL | 仓库 | 没有 constitution，无法检查原则一致性 | 记录在 review_log；本作业不新建 constitution |
| I1 | Inconsistency | HIGH | spec §4 状态表 | DB 的 no_data 包含“计数为 0”，与审阅决定 D1（计数 0 = completed）冲突 | 修改 spec 与代码（P2-count0） |
| I2 | Inconsistency | HIGH | spec §6 | 文中写“对 LLM、embedding、DB、tool 分别设上限”，但 RAG 内部的 BM25 SQL、本地编码、推断中的多条 FTS 语句都没有逐条计数 | 细化计数类别（P2-budget） |
| U1 | Underspecification | HIGH | spec §6 | 截止时间对线程中的同步调用（`asyncio.to_thread`）是否真的能停止后续外部调用，没有定义 | 写明检查点语义并补测试（P0-3） |
| U2 | Underspecification | HIGH | spec §8 | 拒答策略只有一个阈值，没有写明信号来源和有效性门槛 | 按 D2：先在调参集上找新信号，BA > 0.6 才上线（P1-3） |
| C1 | Coverage Gap | MEDIUM | spec §6 Retry | RAG 证据校验重试“最多 1 次”在 chap12 层没有测试达到上限后的显式状态 | 补测试（P2） |
| C2 | Coverage Gap | MEDIUM | 作业 §5 | 固定任务集只有 explain_and_data 一种类型，无法按任务类型报告收益与退化 | 构建混合任务集（P1-1） |
| A1 | Ambiguity | MEDIUM | comparison.md、improvements.md | “整体完成”包含 N 题的错误发布，口径不清；没有可度量的 Success Criteria | 增加“正确完成”和 BA（P1-2） |
| A2 | Ambiguity | MEDIUM | spec §3 | DB Worker 的业务价值（文档计数）与回答之间的关系论证不足 | 重新论证，并评估替代方案（P1-5） |
| F1 | Inconsistency | MEDIUM | plan.md | plan 引用的“spec.md §9”尚不存在 | P1-5 时补上 |
| F2 | Inconsistency | LOW | tasks.md | 不是 Spec Kit 格式（没有阶段、[P] 标记和 T 编号），也没有按任务记录的命令与结果 | 追加执行记录节 |
| F3 | Inconsistency | LOW | contracts.py | v2 修改了 Contract 字段但没有提升 `CONTRACT_VERSION` | 改为 chap12-v2 并记入变更日志 |

## Coverage Summary（推导的需求键）

| 需求键 | 有任务？ | 有测试？ | 备注 |
| --- | --- | --- | --- |
| spec§2-routing | 是 | 是 | test_supervisor |
| spec§4-contract-states | 是 | 是 | 36 种组合 |
| spec§5-db-scope | 是 | 是 | test_db_worker |
| spec§5-rag-scope | **否** | **否** | G1 |
| spec§5-whitelist-size | 是 | 是 | |
| spec§6-budget-deadline | 是 | 部分 | U1、I2 |
| spec§6-retry | 部分 | 部分 | C1 |
| spec§7-non-goals | — | — | |
| 作业§5-comparison-by-type | **否** | **否** | C2 |

**Metrics**：推导的需求键 9 个；有任务覆盖的 7 个（78%）；歧义 2 个；重复 0 个；CRITICAL 2 个（G1、D1）。

**Next Actions**：G1 必须在合并前解决；D1 记录为已知例外；其余问题按工作单的 P0/P1/P2 顺序处理。


---

# 补充：Constitution Alignment（2026-10-17）

执行者：Claude，按 Spec Kit v1.2.1 的 `speckit-analyze` 模板中 “D. Constitution Alignment” 一节，对照草案 `.specify/memory/constitution.md`（1.0.0-draft，**尚未批准**）只读检查。这是代理执行模板得出的结论，不是 CLI 输出。constitution 写于实现之后，因此本节只能说明“现状与原则是否一致”，不能说明实现过程遵守了它。上表 D1（缺少 constitution）由此关闭为“已有草案、待批准”。

| ID | 原则 | 严重度 | 位置 | 发现 | 处理 |
| --- | --- | --- | --- | --- | --- |
| K1 | 开发流程 1（Spec → 人工审阅 → 实现） | CRITICAL | 整个功能 | Spec 写于实现之后，事前没有人工审阅；2026-10-11 只做了 D1–D4 的事后审阅 | 无法事后补救；如实记录（review_log.md），并提供逐条审阅清单 `spec_review_checklist.md`，由人工完成 |
| K2 | II 切分纪律 | HIGH | 确认集 | 原确认集（20261013）在旧配置下已运行一次，之后配置改变（v3） | 新建 confirm2（20261014），当前配置只在它上面做一次真实模型确认 |
| K3 | VI 版本化 Contract | LOW | v1 → v2 | v1 阶段改了字段但没有升版本号 | 已在 chap12-v2 补上并记录 |
| K4 | I 证据先于结论 | — | comparison.md、PR | 离线数字都能追溯到 `evaluation/results/chap12/`；真实模型数字在运行前标为“未执行” | 符合 |
| K5 | III 复用不修改 | — | `src/rag`、`api/main.py` | 本分支对 Project 1 代码、旧 api.main、旧 MultiAgentVersion 均无改动（以 git diff 为准） | 符合 |
| K6 | IV 程序掌握权限 | — | db_worker、product_pick、critic | 无 Text-to-SQL；模型只能在程序给出的候选中选编号，程序再校验；授权在检索时生效 | 符合 |
| K7 | V 有界执行 | — | budget、critic | 所有调用都先预留预算；Replan 最多 1 次 | 符合 |
| K8 | VII 可复现 | — | `.rag_data` | 索引不进 git，但有内容摘要和重建校验（`chap12_rebuild_indices`；2026-10-17 在 4 个切分上重建，结果一致） | 符合 |

结论：除 K1（流程，无法事后补救）外没有新的 CRITICAL；K1 的处理方式是如实披露，并由人工完成审阅清单。
