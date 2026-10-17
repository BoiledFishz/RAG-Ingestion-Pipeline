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

## 已知限制与未完成项

1. **真实模型档位**：在作者的 Windows 机器上用 `chap12_compare_real.ps1` 运行（调参集决策 → 评测集 → confirm2 一次）。结果出来之前，comparison.md 中的真实档位表格保持“未执行”；结果出来后单独提交并更新本描述。
2. 上面“主要结果”是 v2/v3 配置的离线结果；v3（2026-10-17）改动后的离线结果见 comparison.md 的更新。原确认集在旧配置下已用过一次，当前配置的确认结果只来自新建的 confirm2。
3. 拒答没有可靠信号；检索调参未达到登记门槛（R@8 最好只多 0.026）；约 11–22% 的组合题无法确定产品（模型选择产品的效果待真实模型结果）。
4. constitution 只是草案；没有事前审阅；Spec 人工审阅清单待完成。
5. 索引不进入 git，用 `python -m evaluation.chap12_rebuild_indices --rebuild --install` 重建并校验。

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_01Lteh1biz3ahyk3arktla5w
