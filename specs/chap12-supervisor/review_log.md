# 审阅时间线（如实记录）

所有时间为 America/Los_Angeles，2026-10-11。
时间来源：用户消息时间戳、git 提交时间（`git log --date=iso-local`，UTC 已换算）和文件修改时间。不补写、不回填任何日期。

| 时间 | 事件 | 证据 |
| --- | --- | --- |
| 15:32 | 用户给出 Chap12 作业原文，要求数据使用 TechQA 随机 100–200 个样本 | 对话 |
| 约 15:35 | 用户选择交付方式“直接实现代码”，样本含义为“两者都缩小” | 对话（AskUserQuestion） |
| 15:39 | 构建评测样本索引（种子 20261011） | `.rag_data/chap12_sample.sqlite` 的修改时间 |
| 15:40–15:52 | 编写代码与测试 | — |
| 15:50 前后 | 在实现**之后**才写 spec.md、tasks.md、comparison.md、PR_DESCRIPTION.md | 同一提交中首次出现 |
| 15:54:55 | 提交 834cd04（v1：代码 + 文档） | git |
| 16:25–16:58 | v2：调参集、样本 dense、产品推断 | — |
| 16:58:55 | 提交 ab4e8d7（v2） | git |
| 18:11 | 生成交给 AI 评审的材料包 | REVIEW_PACKAGE.md |
| 20:04 | 收到 AI 评审工作单（P0/P1/P2） | 对话 |
| **20:05** | **第一次人工审阅**：用户对 4 个决策点作出决定（见下） | 对话（AskUserQuestion） |
| 20:05 之后 | 按审阅决定修改 Spec 与实现；本文件此时写成 | 后续提交 |

## 不符合流程要求的事实

1. **没有使用 Spec Kit。** 本仓库未初始化 Spec Kit：没有 `.specify/` 目录、没有 constitution、没有 `specify` 命令。spec.md、tasks.md 是手写的，而且写于实现之后。原先也没有 plan.md；现在的 plan.md 是 20:05 之后补写的，并非事前计划。
2. **没有事前人工审阅。** 作业要求“经人工审阅后再生成 Plan 与 Tasks”，实际上第一次人工审阅发生在实现完成约 4 小时后，而且只覆盖下列决策点，不是对整份 Spec 的逐条审阅。
3. 下面的审阅决定都是**事后审阅**，不能当作实现前的批准。

## Spec Kit 状态（20:05 之后查询）

- `uvx --from git+https://github.com/github/spec-kit.git specify version` 的输出为 `CLI Version 1.1.4.dev0`。工具是临时获取的，没有安装进仓库。
- 该 CLI 的子命令只有 `init/check/version/mcp/self/extension/integration/event/preset/artifact/bundle/workflow`。`analyze`、`checklist` 不是 CLI 子命令，而是交给 AI 代理执行的提示词模板（`specify_cli/core_pack/commands/analyze.md`）。
- 按模板，analyze 的前置条件是 spec.md、plan.md、tasks.md 三者齐全，并且有 constitution。仓库原先缺 plan.md，所以按模板规定**应当中止**。补写 plan.md 后，由 Claude 按 analyze 模板执行了一次只读分析，结果见 `analyze_report.md`。那是代理执行模板得出的结论，不是 CLI 输出。仓库仍然没有 constitution，所以 analyze 中的“Constitution Alignment”一项无法检查。

## 人工审阅的决策点与决定（20:05，用户本人）

| # | 决策点 | 选项 | 决定 |
| --- | --- | --- | --- |
| D1 | count=0 的语义 | completed（值为 0）/ no_data | **completed，值为 0**。只有列表查询返回空列表才算 no_data |
| D2 | 拒答策略 | 先在调参集上找新信号，BA ≤ 0.6 就不上线 / 拒答优先阈值 / 保持接受率优先 | **先找新信号，无效再定阈值** |
| D3 | RAG 证据如何按授权产品过滤 | 检索时过滤 / 检索后剔除 | **检索时过滤** |
| D4 | Contract、六态汇合规则、预算默认值（150 s / 8 / 4 / 4 / 4） | 保持并按工作单细化 / 另给意见 | **保持，按工作单细化**（预算计数类别细化） |

每项决定对 Spec 和代码的改动记录在 `contract_changelog.md`。
