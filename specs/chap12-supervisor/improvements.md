# 问题清单与改进（2026-10-11 第二轮）

所有参数选择只在**独立调参集**上完成：从 training 集剩余的 450 题中，用种子 20261012 再随机抽 150 题，与评测样本没有重叠。调参集的索引和金标单独存放（`evaluation/chap12/tune/`），评测样本的 150 题只用于最终报告。

## 已改进

| # | 问题 | 改进 | 证据 |
| --- | --- | --- | --- |
| 1 | 检索只用 BM25，离线词法重排几乎无效（与纯 BM25 相同），R@8 = 0.577 | 新增样本范围内的 dense 检索：直接复制 Project 1 已算好的 MiniLM 向量（`<index>.dense.sqlite`），不重新计算。BM25 + MiniLM 通过 RRF 混合；离线重排沿用 Project 1 的公式（0.5 语义 + 0.3 词覆盖 + 0.2 BM25 先验），语义项换成 MiniLM 余弦 | 调参集上比较了 5 种方案（`tune/retrieval_report_tune.json`），选 MRR 和 R@1/R@5 最高的“hybrid + MiniLM 重排” |
| 2 | 换了重排器之后，Project 1 的验收阈值（按 nomic 分数标定）不再适用 | 在调参集上重新标定：取能保持 Project 1 答案接受率（0.793）的最高阈值，得到 0.5404（`tune/thresholds.json`）。若只最大化 balanced accuracy，会选出只接受 14% Y 题的退化阈值，所以没有采用 | 同上 |
| 3 | 产品槽位只认字面名称，评测集只有 59/150 题能执行数据查询 | 问题中写明产品时仍优先用字面名称；没写明时，由 DB Worker 用**自己的** BM25 前 3 篇文档的官方产品标注来推断（至少 2 篇一致）。结果标记 `product_source=inferred`，并附推断依据的文档 ID 和限制说明。推断后的产品照样做权限检查 | 调参集：可识别题 44 → 98 / 112；与金标文档产品一致的题 29 → 77 |
| 4 | 缺少产品时 DB 返回 `failed`，把“需要用户补充信息”算成了执行失败 | 改为 `no_data` + `clarification_required` | 测试 `test_missing_product_needs_clarification_not_failure` |
| 5 | 对照脚本不输出 R@k / MRR，也不报告产品来源 | 加入 R@1/3/5/8、MRR，以及产品来源分布和“产品与金标文档一致率”（代理指标） | `chap12_compare.py` |

## 评测样本结果（offline，n = 150；v1 = 第一轮，v2 = 本轮）

| 指标 | v1 | v2 |
| --- | --- | --- |
| 检索 R@1 / R@5 / R@8（123 道 Y 题） | 0.423 / 0.545 / 0.577 | **0.496 / 0.618 / 0.683** |
| MRR | 0.481 | **0.543** |
| Y 题发布答案 | 71/123 | **101/123** |
| Y 题引用了金标文档 | 47/123 | **60/123** [0.40, 0.58] |
| Y 题 token F1（未发布记 0） | 0.195 | 0.201 |
| **N 题拒答（代理指标）** | **16/27 = 0.59** | **8/27 = 0.30（退化）** |
| 数据结果产出 | 59/150 | **125/150**（字面 59，推断 66；25 题需要澄清） |
| 数据结果与独立复算一致 | 59/59 | 125/125 |
| 数据产品与金标文档产品一致（代理） | — | 71/100（字面 32/47，推断 39/53） |
| Multi-Agent 整体完成 | 35/150 | **101/150** |
| Multi-Agent 平均延迟 | 304 ms | 381 ms |

两个系统的 RAG 部分逐题相同；单 Agent 仍然无法提供数据部分，整体完成为 0/150。

## 仍存在的问题（未解决）

1. **还没有在真实模型上运行。** 当前所有数字都来自 offline 档位（规则改写 + 抽取式选证），本环境无法连到你电脑上的 Ollama。ollama 档位默认用 nomic 重排，也可以设 `CHAP12_RERANKER=minilm` 对比两者。
2. **拒答下降**：v1 拒答 16/27，v2 只有 8/27。原因是阈值改为保持 Project 1 的答案接受率，而重排分数几乎无法区分 Y 题和 N 题（调参集上 balanced accuracy 只有 0.49）。离线档位中阈值是唯一的拒答机制；真实档位还要靠 LLM 的证据选择和适用性复核来拒答，效果待测。
3. **产品推断约有 1/4 不一致**（以金标文档的产品标注为代理）。已在结果中标注来源和限制说明；更可靠的做法是让 LLM 从目录中选择、再由程序校验，这一方案没有实现。
4. Token 数仍为 null，因为复用的 Ollama 适配层不返回 token 计数。
5. 规格是和实现同批交付的，尚未人工审阅。
6. mypy 剩余的 2 个错误都在已有的 `src/rag/techqa/claims.py` 和 `semantic.py` 中，不是本次引入的。
7. 样本索引和 dense 附属文件在 `.rag_data` 下，不进入 git，需要按下面的命令重建。

## 重建命令

```powershell
cd enterprise-ai-agent; $env:PYTHONPATH="../src;."
python -m evaluation.chap12_build_sample                       # 评测样本（种子 20261011）
python -m evaluation.chap12_build_sample --seed 20261012 --index ../.rag_data/chap12_tune.sqlite `
  --output evaluation/chap12/tune --exclude-manifest evaluation/chap12/sample_manifest.json
python -m evaluation.chap12_build_dense --index ../.rag_data/chap12_sample.sqlite
python -m evaluation.chap12_build_dense --index ../.rag_data/chap12_tune.sqlite
python -m evaluation.chap12_retrieval_tune --split tune        # 方案比较 + 阈值标定
```

---

# 第三轮（AI 评审工作单，2026-10-11 20:05 之后）

逐项记录（改动、命令、结果）见 tasks.md 的“工作单执行记录”；对照结果见 comparison.md。

## 已完成

| 工作单项 | 结果 |
| --- | --- |
| P0-1 流程 | 新增 review_log（如实的时间线，确认没有事前审阅、没有使用 Spec Kit）；Spec Kit 1.1.4.dev0 的 analyze 由代理按模板执行，结果见 analyze_report.md；人工审阅 4 个决策点（D1–D4，事后）；新增 contract_changelog |
| P0-2 权限 | RAG 在检索时按授权产品过滤（在 RRF 之前，两路检索都过滤），父文档展开前再检查一次；DB 推断只在授权文档中进行；新增泄漏测试 4 项 |
| P0-3 截止时间 | 每条 SQL、LLM 调用、embedding、本地编码之前都检查截止时间，线程被放弃后不能再发起新调用；用真实 `time.sleep` 阻塞线程的测试 3 项 |
| P0-4 真实评测 | 提供 ps1/sh 脚本（记录 digest、3 次重复、分层子集、只在调参集上标定 nomic、确认集只运行一次）；token 采集；**真实运行未执行** |
| P1-1 混合任务集 | explain 76 / explain_and_data 74 / data 60，data 题有独立复算的金标 |
| P1-2 指标 | 正确完成、BA、阈值曲线、Project 1 原配置基线；failed 44→0 拆分为：产品推断补救 33，状态重新归类 11 |
| P1-3 拒答信号 | 研究了 5 个信号，只有 top-1/top-2 间隔的 BA 为 0.614（调参集，刚过 0.6），按事先规则采用；**确认集上没有复现**（BA 0.536，Project 1 原配置为 0.521） |
| P1-4 确认集 | 种子 20261013，冻结配置 2f7fe55，只运行一次（offline） |
| P1-5 DB 价值 | explain_and_data 改为返回“相关文档”；“先解析产品、再同时过滤 RAG”的替代方案在调参集上更差（R@8 0.661 vs 0.688，并增加 124 ms 延迟），未采用 |
| P2 | count=0 归为 completed（D1）；证据校验重试达到上限的显式状态测试；预算细分 sql/local/缓存命中计数；Python 3.11 下 157 个测试通过；uvicorn + curl 冒烟测试 |

## 仍存在的问题

1. **真实模型档位未执行**：所有质量数字都来自 offline（0 次 LLM 调用）；token 采集只经过 mock 的管线连通性验证。
2. **拒答没有可靠信号**：top-1 分数的 AUC 为 0.53；间隔门槛在调参集上的 BA 0.614 是在样本内取的最优值，确认集只有 0.536，同时还以少答 Y 题为代价。
3. **“相关文档”对回答帮助很弱**：列表包含金标文档的比例只有约 7%。
4. 约 11–22% 的 explain_and_data 题无法确定产品，只能返回 clarification。
5. 流程：没有事前审阅；PR 待创建并等待 Review。
6. `.ps1` 在本环境中没有 PowerShell，未验证。
