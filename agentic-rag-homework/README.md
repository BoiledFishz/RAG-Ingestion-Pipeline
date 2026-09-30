# Agentic RAG 与 Multi-Agent 课后作业

这是同一仓库内按独立目录运行的实验项目，覆盖 Agentic RAG、LLM Planner、ReAct Research
Agent、Critic Loop，以及 Single/Multi-Agent 对照实验。默认使用可复现的离线结构化模型
模拟器；设置环境变量后，Planner、ReAct 和 Critic 可切换到真实 Ollama Structured Output。

## 作业要求对应关系

| 要求 | 实现位置 | 验收点 |
| --- | --- | --- |
| Query Rewrite | `agents/rag_agent/service.py` | 模糊问题澄清；明确问题保守改写 |
| Retriever Tool | `tools/retriever.py` | 封装余弦向量数据库检索，限制 Top-K |
| Context Compression | `ContextCompressor` | Top-K 文档压缩成直接相关完整句子 |
| Structured Output | `models/schemas.py` | `answer / sources / confidence` 强校验 |
| LLM Planner | `agents/planner.py` | JSON Schema、Agent 枚举、顺序 ID、DAG 校验、失败修复一次 |
| ReAct Research | `agents/research.py` | 首次 RAG 后自主选择 Search、Document Retrieval 或停止 |
| Critic Loop | `agents/critic.py` | Feedback 回灌，记录已解决问题，最多 Retry 两次 |
| Single vs Multi | `agents/systems.py` | 统一 Metrics 与同一测试集公平对比 |
| 实验报告 | `evaluation/run.py` | 输出逐题 trace、指标表和结论 |

## 目录

```text
agentic-rag-homework/
├── api/                    # FastAPI 服务
├── agents/
│   ├── rag_agent/          # Agentic RAG
│   ├── planner.py          # Structured Output LLM Planner
│   ├── research.py         # Fixed 与 ReAct
│   ├── critic.py           # Diagnosis/Critic feedback loop
│   └── systems.py          # Single 与 Multi-Agent
├── tools/                  # RAG、Search、Document Retrieval Tools
├── vectorstore/            # 独立内存余弦向量索引
├── models/                 # 严格 Schema、Ollama 和计量器
├── data/                   # 合成知识库及离线外部检索语料
├── evaluation/             # 数据集、实验入口及输出
└── tests/                  # 功能和边界测试
```

## 安装与测试

从本目录执行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
```

在当前父项目已经配置好的环境中也可以执行：

```powershell
..\.venv\Scripts\python.exe -m pytest
..\.venv\Scripts\python.exe -m evaluation.run
```

评测生成：

- `evaluation/results/report.md`：可直接提交的指标表和结论；
- `evaluation/results/runs.json`：三类 RAG 问题、Planner 稳定性、每轮 Critic 问题、
  Fixed/ReAct 轨迹以及 Single/Multi 完整原始指标。

## 启动 API

```powershell
..\.venv\Scripts\python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8002
```

接口：

- `POST /v1/rag/query`
- `POST /v1/planner`
- `POST /v1/research`
- `POST /v1/critic-loop`
- `POST /v1/single-agent`
- `POST /v1/multi-agent`
- `GET /healthz`

请求示例：

```json
{"query": "How do I investigate EKS CrashLoopBackOff?"}
```

## 使用真实 Ollama LLM

默认 `MODEL_PROVIDER=demo`，便于老师直接运行和复现实验。要验证真实 LLM Planner 和
ReAct 决策，在启动 API 前设置：

```powershell
$env:MODEL_PROVIDER = "ollama"
$env:OLLAMA_MODEL = "llama3.2:3b"
$env:OLLAMA_URL = "http://localhost:11434"
..\.venv\Scripts\python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8002
```

Ollama 返回值仍会经过完全相同的 Pydantic Schema、Agent allow-list 和 DAG 校验。
评测也必须显式选择真实模型，命令与输出如下：

```powershell
..\.venv\Scripts\python.exe -m evaluation.run --provider ollama --planner-runs 10 `
  --output evaluation/results/ollama
```

真实报告见 [Ollama 实验](evaluation/results/ollama/report.md)，模拟器报告位于
`evaluation/results/report.md`。两者 Token 都是统一正则估算值，不是供应商账单 Token。
ReAct 的决策使用真实 LLM；两个版本的工具共用 Hash 内存索引和离线外部检索语料，
Search Tool 不表示联网搜索。普通 `/v1/rag/query` 使用确定性改写/压缩与抽取式回答。

Supervisor 会按校验后的 DAG 实际分派每个 task，依赖输出只传给显式声明依赖的节点。
Research 和 Diagnosis/Critic 使用 LLM；Data Analyst 和 Report Writer 是确定性证据处理器。
每个任务的 `objective`、依赖、输出和状态记录在 `executions`；最终答案来自终端节点。
报告保留诊断正文，不能用来源文本覆盖正文从而掩盖生成问题。

非法文档 ID、重复动作或证据不足时过早结束，会触发一次有界补充搜索。
Diagnosis 使用结构化 `citations` 字段，Critic 除事实评审外还做引用存在性检查，最多重试两次。
失败会记录 `fallback` 并返回已验证的抽取证据，报告单独列出降级次数。

## 实验定义

- Answer Quality：仅答案正文的参考事实覆盖比例，来源引文和引用编号不计分；未知问题必须实际拒答。
- Failure Rate：质量分低于 1 或运行异常的比例；异常保留在分母并计 0 分。
- Fallback cases：发生诊断降级的题数，独立于最终答案的质量分统计。
- LLM Calls：由 `MeteredModel` 在每次 Structured Output 请求时计数。
- Token Usage：所有 Prompt 和模型输出的可复现估算总和。
- Latency：单次工作流端到端墙钟时间。
- Hallucination：知识库不存在答案时仍返回来源或实质答案，记为失败。

小型合成集用于展示测量方法，不足以证明生产效果。正式实验应替换为独立留出集，多次运行
真实模型，并报告平均值、方差、模型版本和硬件环境。

## 最终结论

**Multi-Agent 不一定优于 Single Agent。** 多 Agent 的专业分工与独立复核适合复杂、可拆解、
高风险任务，但 Planner、跨 Agent 交接和 Critic 都会增加调用、Token、延迟与失败点。简单问题
通常由 Single Agent 更经济地完成；只有实测质量收益超过协调成本时，Multi-Agent 才更合适。
