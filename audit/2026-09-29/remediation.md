# 验收问题修复与复验

完成日期：2026-09-30（America/Los_Angeles）。本报告对应原验收报告的五类问题，
原报告及失败证据保留在同目录，避免把修复前结果与修复后结果混在一起。

## 结论

代码错误、测试复现问题和原环境阻塞已修复；默认真实模型入库、三种查询模式、
Enterprise core/full API、Agentic API 和评测流程均已实际执行。
全量 TechQA Hash 基线仍有明显的检索质量限制，不能据此声明生产效果达标。

| 原问题 | 修复 | 复验结果 |
|---|---|---|
| 缺少 Embedding 模型 | 下载 `nomic-embed-text`，CLI/API 自动加载 `.env`，单独使用 `aws_support_nomic` | 实际返回 768 维；混合语料 28 个 Chunk 全部写入 |
| 全量 Qdrant 未启动 | 隔离 Docker 失效运行时 socket 目录，恢复原容器和数据卷 | `/readyz` 200；`techqa_full_hash` 为 2,826,591 点 |
| 根目录 pytest 导入冲突 | 限定根测试目录，新增独立进程统一测试入口 | 根 29、Enterprise 37、Agentic 22，共 88 项通过 |
| Enterprise 依赖未提交数据 | 单测使用小型 fixture；官方数据评测单独运行 | 无官方数据的干净源码副本 37 项通过 |
| 旧 API 冒烟问题不属于当前语料 | 使用 Streams 4.1.1.2 问题，同时断言文档来源和答案正文 | core/full 的明确、模糊、未知三类请求均通过 |
| Embedding 失败仍返回 0 | 按解析 Chunk 的实际写入/跳过数决定退出码，finally 关闭数据库 | 故障注入返回 1；随后重试和幂等重跑均返回 0 |
| 摘要在词中间截断 | 长度为软目标，保留完整首句；模型 token 截断走兜底 | 版本号和长句回归通过；真实 28 个摘要无兜底 |
| 降级后误用分数阈值 | 保留检索排序，单独使用 Query 词项覆盖率门控 | 15 题注入重排故障：12 个可回答问题通过门控，3 个未知问题拒答 |
| Plan 未决定执行 | 按 DAG 分派四类注册角色，只传入显式依赖；保留每个任务结果 | 三种不同依赖计划、无隐藏检索、依赖隔离测试通过 |
| 来源文字给答案“代答” | 只对答案正文计分，剔除来源引文和引用编号 | 泛泛正文即使附有正确引文也得 0 分 |
| ReAct / Critic 真模型失败 | 非法文档 ID/过早结束有界恢复；诊断结构化引用并进行程序校验 | 原 EKS ReAct 与 Lambda Critic 用例通过；最大重试两次回归通过 |
| Agent 目录未进入提交 | 两个目录作为同仓库子项目提交，数据包、向量库和 `.env` 均忽略 | 提交只包含源码、小型语料、文档和评测结果 |
| 远端标签未确认 | 只读核验远端 annotated tag 的 peeled commit | 三个标签均存在且与本地一致，未移动历史标签 |

## 真实模型与入库

`python main.py data/aws_support_test_corpus/data`：6 个文件中 4 个成功解析，
空文件和坏 PDF 记录 WARNING 后跳过，扫描 PDF 经过 OCR；28 个 Chunk 写入。
第二次运行全部 28 个跳过，没有重复摘要或 Embedding 调用。
全部记录具备 `source_file/page_number/chunk_hash/context_summary`。
旧 Hash collection 与新 nomic collection 分离，避免混用 384/768 维向量。

根 API 使用真实 `llama3.2:3b` 与 nomic 向量：Dense/Sparse/Hybrid 明确问题均返回来源；
未知问题和不存在的 source_file 拒答；空 query 返回 422。引用 ID 有效并不等同于全部
事实已被验证，生产应用仍需更强的答案忠实度评测。

Ragas 使用全新临时数据库复测 5 个黄金对：256 字符切片 17 个 Chunk，512 字符切片
8 个 Chunk，`IDBasedContextRecall` 均为 1.0。这是证据 ID 召回指标，不是 LLM 事实评分。
详情见 [Ragas 输出](../../evals/remediation_ragas_results.json)。

15 题真实向量检索结果见 [检索输出](../../evals/retrieval_nomic_results.json)。Dense
Recall@5 为 1.0，Dense+词法重排为 0.917，Hybrid+词法重排为 0.833。
阈值与结果使用同一校准集，不视为独立留出集；词法重排在本小集上没有改善语义召回。
降级门控阈值 0.183333 的 API 测试使用计数生成器，目的仅为验证拒答短路，未冒充真实答案质量。

## Agent 实验

真实模型实验：5 题，Fixed/ReAct/Single/Multi 的答案正文参考事实覆盖率均为 1.0；
运行错误和诊断降级均为 0。Single 平均 2.4 次 LLM 调用、1549 个估算 Token，
Multi 为 3.8 次和 2220.4 个。10 次相同任务的 Planner Schema 均有效，非法 Agent 输出为 0。
详见 [真实报告](../../agentic-rag-homework/evaluation/results/ollama/report.md)。

模拟器实验也重新运行并保留了每轮 Critic 问题及反馈。模拟器用于确定性回归，不能替代真模型。
Research、Diagnosis 和 Critic 使用 LLM；分析与报告节点是确定性证据处理器。
两个实验版本共用内存 Hash 索引和离线 Search 语料；普通 RAG 端点是确定性改写/抽取式回答。
这些边界已写入 README，未将离线语料检索描述成联网 Research。

## 全量 TechQA 的额外发现

全量库恢复后，原 Hash 检索把 Streams 的版本问题误答成其他产品的环境变量说明。
增加了标题全文索引，以及“产品 + 版本”的有界补充召回；两路保留相同 Metadata Filter。
压缩器要求检索文档包含请求的完整版本号。修复后正确返回 `techqa://swg21996508`。
全文索引需显式执行 `python -m vectorstore.indexes`，不在用户查询时创建。

首次全量评测出现 1 次 gRPC Protobuf 解码错误；默认传输改为 REST 后重新完整运行：

| 官方开发集 | 结果 |
|---|---:|
| 总题数 / 可回答 / 不可回答 | 310 / 160 / 150 |
| Hit@5 / Hit@10 | 0.19375 / 0.21875 |
| MRR | 0.19076 |
| 不可回答问题拒答准确率 | 0.54667 |
| 平均评测耗时（额外检索 + Agent） | 332.28 ms |
| 运行错误 | 0 |

输出保存在 [完整评测目录](../../enterprise-ai-agent/evaluation/results/full_hash_remediation/summary.json)。
异常题保留在类别分母，按失败计分。以上结果证实可运行性，不代表全量答案质量达标；
后续应在新 collection 中使用语义 Embedding，并用独立留出集校准。原 core Hash 评测属于
不同数据范围，不能直接当作本次全量成绩或与其声称同条件提升。

## 运行与环境说明

```powershell
# 根目录；已安装 README 中的依赖和 Tesseract
./scripts/start-local.ps1
python main.py data/aws_support_test_corpus/data
python scripts/test_all.py
rag-api

# 全量 TechQA
./scripts/start-local.ps1 -FullTechQA
cd enterprise-ai-agent
../.venv/Scripts/python.exe -m vectorstore.indexes
../.venv/Scripts/python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8001
# 另一个使用相同项目环境的终端
../.venv/Scripts/python.exe -m evaluation.smoke_api
```

`start-local.ps1` 保留已有 `.env`，跳过已安装模型；Docker 命令由外层超时保护，
失败会明确返回非零。单机嵌入式 Qdrant 的同一路径只能由一个进程打开。

本机 Docker Desktop 4.81.0 出现过反复的 Windows AF_UNIX socket 残留问题，
日志分别指向 `%LOCALAPPDATA%/Docker/run/dockerInference` 与
`%LOCALAPPDATA%/docker-secrets-engine/engine.sock`。本次停止失败实例后，将两个
运行时目录改名为 `.stale-20260929*` / `.stale-20260930` 备份并重建，容器卷未删除。
这种系统问题仍可能在异常退出后复发；启动脚本会有界报错，不会自动清空数据或重置 Docker。
相同错误的上游报告见 [Docker desktop-feedback #448](https://github.com/docker/desktop-feedback/issues/448)。

## Git 与证据

远端 `https://github.com/BoiledFishz/RAG-Ingestion-Pipeline.git` 标签核验：

| 标签 | 目标提交 |
|---|---|
| retriever-v1-dense | 28e5262ed64268ef8e2d052fba697961f33efb25 |
| retriever-v2-rerank | 2eff89d5fab2b75501afa07d5ac0f366056243e1 |
| retriever-v3-hybrid | b5e29494cc3b5b6a6597785a58c8b07bc7cef0cc |

本次修复使用 `codex/aws-support-ingestion` 分支，保留历史标签。
测试、HTTP、数据库健康检查和门控记录见 [remediation](remediation/tests.txt)。
Ruff 全部通过；根项目 MyPy 30 个文件通过，Enterprise MyPy 26 个文件通过。
测试依赖有一条 FastAPI/Starlette 的弃用提示，不影响当前测试通过。
