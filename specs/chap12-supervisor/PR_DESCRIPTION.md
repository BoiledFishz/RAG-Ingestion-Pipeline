# Chap12：Supervisor–Worker 骨架（TechQA 随机 150 题样本）

## 审阅时间线（如实说明）

- Spec、Tasks 和实现是同批完成的（2026-10-11 15:32–16:58 PT），**没有事前人工审阅，也没有使用 Spec Kit**。plan.md 是事后补写的。
- 第一次人工审阅在 2026-10-11 20:05（PT），是**事后审阅**，只覆盖 D1–D4 四个决策点。详见 `specs/chap12-supervisor/review_log.md`。
- 一致性检查：用 Spec Kit 1.1.4.dev0 的 analyze 模板，由代理执行（不是 CLI 输出），结果见 `analyze_report.md`；其中 2 项 CRITICAL，一项已修复（RAG 未按授权过滤），另一项是没有 constitution。
- 2026-10-17：用 Spec Kit v1.2.1 初始化 `.specify/`，写了 constitution **草案**（1.0.0-draft，未批准，写于实现之后），并补做了 Constitution Alignment 检查；“实现先于 Spec、无事前人工审阅”记为无法事后补救的 CRITICAL。整份 Spec 的人工审阅清单见 `spec_review_checklist.md`，**尚未由人完成**。
- 本 PR 的目标分支是 `codex/project2-course-completion`（本分支的起点），所以 diff 只包含 Chap12 的改动。
- 本 PR **未合并**，等待 Review。

## 内容

- `enterprise-ai-agent/agents/chap12/`：
  - Supervisor：确定性计划，RAG 与 DB 并行，六种状态的程序化汇合；
  - RAG Worker：原样复用 Project 1 的 RAGAgent；
  - DB Worker：3 个参数化只读模板，加上产品推断；
  - 权限：scope.py，检索时按授权产品过滤；
  - 预算：budget.py / metered.py，按 llm / embedding / db / tool / sql / local 分类计数，并在线程内检查截止时间；
  - 其他：dense.py（样本内 MiniLM）、ollama_tokens.py（token 采集）；
  - 2026-10-17（Contract chap12-v3）：产品内按问题相关性排序的“相关文档”、模型从候选列表选择产品并由程序校验（product_pick.py）、程序 Critic 与最多 1 次 Replan（critic.py，按调参集规则默认关闭）。
- `api/chap12_main.py`：`POST /v1/chap12/analyze`，凭证由服务端管理。没有修改 Project 1 代码、旧的 `api.main` 或旧的 MultiAgentVersion。
- 评测：样本、调参集、确认集的构建；混合任务集；三系统对照（`chap12_eval.py`）；拒答信号研究；产品过滤替代方案研究；表格生成脚本（`chap12_report.py`）；真实模型脚本 `chap12_compare_real.ps1` / `.sh`。
- 文档：`specs/chap12-supervisor/`（spec、plan、tasks 含逐项执行记录、comparison、improvements、review_log、contract_changelog、analyze_report、spec_review_checklist）；`.specify/`（Spec Kit v1.2.1 与 constitution 草案）。
- 可复现：`evaluation/chap12_rebuild_indices.py` 与 `index_digests.json`；4 个切分重建后内容一致（`results/chap12/rebuild_verify_20261017.json`）。

## 实际运行的命令与结果（本机 Linux VM）

| 命令 | 结果 |
| --- | --- |
| `pytest tests/chap12 -q`（Python 3.12.15，2026-10-17） | `137 passed` |
| `pytest tests -q --ignore=tests/project2`（Python 3.11.17） | `157 passed` |
| `ruff check agents/chap12 tools/sample_retriever.py evaluation/chap12_*.py tests/chap12` | `All checks passed!` |
| `mypy --python-version 3.12 agents/chap12 ... evaluation/chap12_*.py`（20 个文件） | `Success: no issues found` |
| `mypy agents/chap12 api/chap12_main.py tools/sample_retriever.py`（Python 3.11 环境） | `Success: no issues found in 15 source files` |
| `python -m evaluation.chap12_eval --split sample ...`（offline） | `evaluation/results/chap12/offline_v3_sample_rotated/` |
| `python -m evaluation.chap12_eval --split confirm ...`（offline，冻结配置 2f7fe55，只运行一次） | `evaluation/results/chap12/offline_v3_confirm_once/` |
| `uvicorn api.chap12_main:app` + curl | `evaluation/results/chap12/uvicorn_smoke.txt`（200 / 401 / permission_denied / 422） |
| `bash -n evaluation/chap12_compare_real.sh`，以及接 mock Ollama 的管线连通性测试 | 通过（只验证连通性，mock 输出没有提交） |
| 调参集研究（2026-10-17）：`chap12_product_study`、`chap12_retrieval_sweep`、Critic 开/关 | `tune/product_study.json`、`tune/retrieval_sweep.json`、`results/chap12/tune_critic_{on,off}/` |
| `python -m evaluation.chap12_rebuild_indices --rebuild` | 4 个切分内容一致 |

## 主要结果（offline，没有调用 LLM；完整表格见 comparison.md）

- data 题：Multi-Agent 正确率 1.000（60/60），两种单 Agent 都是 0。
- explain_and_data：只有 Multi-Agent 能完成，正确完成率为评测集 0.351、确认集 0.311；数据部分没有一条算错，不一致的全部是无法确定产品时返回的 clarification。
- 检索：当前配置相比 Project 1 原配置，在评测集和确认集上 R@8 都有提升（全部 Y 题：0.577→0.683，0.681→0.735）。
- 拒答：间隔门槛在评测集上的 BA 为 0.674，**确认集上只有 0.536，没有复现**；不宣称拒答能力有提升。

## 真实模型结果（qwen2.5:7b + nomic，作者 Windows 笔记本，2026-10-17；表格见 comparison.md）

| 集合 | Multi-Agent 正确完成（全部 90 题） | 单 Agent | Project 1 原配置 |
| --- | --- | --- | --- |
| 评测集（每类 30 题 × 3 次重复） | 0.511 [0.41, 0.61] | 0.089 | 0.089 |
| confirm2（一次） | 0.611 [0.51, 0.71] | 0.167 | 0.156 |

- 收益来自 data 与组合题的任务覆盖；explain 题上三者无可确认差异，离线看到的检索提升在真实档位未得到确认。
- 拒答无效：调参集上 nomic 的 5 个信号都没过 BA > 0.6，真实档位不启用拒答门槛。
- 1,080 条真实运行中 1 次超时（Project 1 原配置），Multi-Agent 无失败；Multi-Agent 平均每题 2.0 次 LLM 调用、约 4.4k prompt token，平均延迟 6.7–7.6 s。

## 第二轮改进（2026-10-18，规则事先登记，见 comparison.md）

- 调参集：加大候选数（12/16 篇）不采用（0.340 对 0.353）；真实档位开启 Critic 采用（组合题 0.360 对 0.333）。
- 评测集同一批 90 题：Multi-Agent 正确完成 0.511 → 0.511；组合题数据正确 0.867 → 0.967，产品一致 0.667 → 0.619。**调参集上的提升没有在评测集上复现**；没有新的确认集可用（600 道 training 题已全部分配，dev 为协议 held-out）。
- 完成率的瓶颈在 RAG 本身（检索排序、引用选择、拒答），不在 Supervisor 层。

## 第三轮：cross-encoder 重排（2026-10-18，规则事先登记，见 comparison.md）

- 筛选（调参集，无 LLM）：ms-marco-MiniLM R@8 0.696、bge-reranker-base 0.732，均高于 nomic 0.661 + 0.03，进入真实模型比较。
- 真实模型调参集（150 题）：正确完成 ms-marco-MiniLM 0.373、bge 0.327，当前配置 0.367；均未达 +0.03 → **不采用，保留 nomic**，评测集未重跑。召回更高，但排第 1 的文档和 Y 题接受率都变差。
- 本轮 Ollama 为 0.40.6，基线为 0.40.5；第四轮在 0.40.6 上重跑基线，150 条结果逐题完全相同。

## 第四轮：cross-encoder 只排序、nomic 阈值决定接受（2026-10-19，规则事先登记，见 comparison.md）

- 调参集 150 题，同一 Ollama 版本：正确完成 ms-marco-MiniLM 排序 0.367、bge 排序 0.333，当前配置 0.367 → **不采用，保留 nomic**，评测集未重跑。
- 保留 nomic 阈值后 Y 题接受率回升，但正确完成率不变：cross-encoder 让答案文档排第一的次数变少，模型引用金标文档也随之变少。

## 复盘与第五轮（2026-10-19，规则事先登记，见 retrospective.md 与 comparison.md）

- 失分拆分（调参集当前配置 150 题）：不可回答题未拒答 32、答案文档不在前 8 篇 39、检索到但未引用或被拒 21、数据错误 3；第 2–4 轮只动了排序。配对比较补算：第 2–4 轮没有一个变体可区分（双侧 p ≥ 0.31）。
- 可回答性核验 Worker：正确完成 0.367 → 0.420（变对 20 / 变错 12），N 拒答率 0.158 → 0.684，但 Y 接受率 0.839 → 0.536 → **不采用**（门槛 −0.05）。
- qwen2.5:14b：0.367 → 0.393（11 / 7，p = 0.24），延迟 3.45 倍 → **不采用**。评测集未重跑。
- 第六轮分级核验（看完整证据，1–5 分）：比二元核验准（净胜 +12 时丢失正确答案 8 道，二元为 12 道），但没有阈值满足“丢失 ≤ 3 且净胜 ≥ 5” → **不采用**，阈值运行与评测集均未执行。

## 已知限制与未完成项

1. 真实模型档位已运行（见上节）；每类只有 30 题，CI 宽；`.ps1` 只在作者的 Windows 机器上验证过。
2. 上面“主要结果”是 v2/v3 配置的离线结果；v3（2026-10-17）改动后的离线结果见 comparison.md 的更新。原确认集在旧配置下已用过一次，当前配置的确认结果只来自新建的 confirm2。
3. 拒答没有可靠信号；检索调参未达到登记门槛（R@8 最好只多 0.026）；约 11–22% 的组合题无法确定产品（模型选择产品的效果待真实模型结果）。
4. constitution 只是草案；没有事前审阅；Spec 人工审阅清单待完成。
5. 索引不进入 git，用 `python -m evaluation.chap12_rebuild_indices --rebuild --install` 重建并校验。
6. 检索召回是第二大失分（调参集 39/150 题答案文档不在前 8 篇），本 PR 不再处理：现成 cross-encoder 与加深候选都无净效果（配对比较见 `results/chap12/paired_retro.json`）；在 TechQA 上微调检索/重排没有不泄漏评测的训练数据，按产品名、错误码改写查询属于 Project 1。复盘见 `specs/chap12-supervisor/retrospective.md`。

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_01Lteh1biZ3ahyK3arKtLa5w
