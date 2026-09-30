# Enterprise TechQA Agent

这是独立于仓库原 Ingestion/Retrieval Pipeline 的 Agentic RAG 服务。知识库已切换为
[IBM TechQA](https://github.com/IBM/techqa)，运行时不再读取原来的 AWS 伪造语料。

## 数据范围

| scope | 内容 | 用途 |
|---|---|---|
| `core` | 600 条训练问题、310 条开发问题、验证集及其候选 Technotes | 快速开发和官方 QA 评测 |
| `full`（默认） | 上述文件 + 官方 801,998 篇 Technotes | 完整知识库检索 |

数据包来自 `PrimeQA/TechQA`，归档文件 SHA-256 固定为
`6b094ef9a69718f727ce8d7e15c4d961e51032cefaa952e0d6af9d176d7ba118`。
程序会先校验哈希，再安全解压；不会使用 `extractall`。完整 bzip2 语料是一个顶层 JSON
数组，程序通过 `ijson` 流式遍历数组元素，所以不会一次性将数 GB 数据载入内存。

## 数据流

```text
官方 TechQA.tar.gz -> SHA-256 校验 -> 安全选择性解压
 -> 流式遍历全部文档 -> 递归边界切片 -> Hash/Ollama Embedding
 -> Qdrant techqa_* collection -> Retriever Tool -> Agent
 -> Query Rewrite -> Context Compression -> {answer, sources, confidence}
```

每个 Chunk 带有 `techqa_document_id`、`title`、`productName`、字符范围等元数据；
`source_file` 使用 `techqa://<document-id>`。`page_number` 表示 Technote 内的 Chunk 顺序，
不是 PDF 页码。Qdrant 写入以文本 SHA-256 派生 ID，重复执行会在 Embedding 前跳过已有数据。

## 安装

在 `enterprise-ai-agent` 目录运行：

```powershell
..\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

## 导入 TechQA

全量数据推荐使用独立 Qdrant 服务。下面的命令只需执行一次；Docker volume 会跨容器重启保留数据：

```powershell
docker run -d --name techqa-qdrant --restart unless-stopped `
  -p 6333:6333 -p 6334:6334 `
  -v techqa-qdrant-storage:/qdrant/storage qdrant/qdrant:v1.18.0
```

快速导入官方训练/验证相关语料：

```powershell
$env:AGENT_COLLECTION = "techqa_hash"
..\.venv\Scripts\python.exe -m vectorstore.seed --scope core
```

完整导入 801,998 篇 Technotes（默认）：

```powershell
$env:AGENT_PROFILE = "offline"
$env:AGENT_EMBEDDING_PROVIDER = "hash"
$env:AGENT_QDRANT_URL = "http://127.0.0.1:6333"
$env:AGENT_COLLECTION = "techqa_full_hash"
..\.venv\Scripts\python.exe -m vectorstore.seed --scope full --batch-size 4096
..\.venv\Scripts\python.exe -m vectorstore.indexes
```

完整导入会生成远多于 801,998 个 Chunk，耗时和磁盘取决于机器。命令可安全重跑；
已写入 Chunk 不会重复 Embedding。生产环境建议用 `AGENT_QDRANT_URL` 指向独立 Qdrant，
本地嵌入式 Qdrant 更适合 `core` 开发集。

`vectorstore.indexes` 显式建立标题全文索引，不在 API 请求中触发大规模索引构建。
Hash 检索遇到“产品 + 版本”问题时会并行补充受标题词项约束的有限候选，两路使用相同的
强制 `published` 和用户 Metadata Filter；标题检索失败时记录日志并使用原候选。
版本号作为完整词项参与排序，压缩器拒绝用其他版本的内容作答。
该补充检索使用 Qdrant 的 [全文过滤](https://qdrant.tech/documentation/search/filtering/)。

默认切片参数为 1200 字符、160 字符重叠、每批 128。可以用
`--chunk-size`、`--chunk-overlap`、`--batch-size` 修改。切换参数时应使用新的 collection，
避免混合不同切片版本。

## 启动与调用

若只验证本机已有的 core 库，使用下列配置可避免依赖 Docker：

```powershell
Remove-Item Env:AGENT_QDRANT_URL -ErrorAction SilentlyContinue
$env:AGENT_PROFILE = "offline"
$env:AGENT_EMBEDDING_PROVIDER = "hash"
$env:AGENT_COLLECTION = "techqa_hash"
..\.venv\Scripts\python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8001
```

全量库需要 Qdrant 服务；已有容器执行 `docker start techqa-qdrant`，不要重复创建或清空卷。
仓库根目录的 `./scripts/start-local.ps1 -FullTechQA` 可准备模型并启动/复用容器。
以下为全量配置：

```powershell
$env:AGENT_PROFILE = "offline"
$env:AGENT_EMBEDDING_PROVIDER = "hash"
$env:AGENT_QDRANT_URL = "http://127.0.0.1:6333"
$env:AGENT_COLLECTION = "techqa_full_hash"
..\.venv\Scripts\python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8001
```

另开 PowerShell：

```powershell
$body = @{
  query = "User environment variables are not picked up after upgrading Streams 4.1.1.2"
  filters = @{ document_type = "ibm_technote" }
} | ConvertTo-Json -Depth 5

Invoke-RestMethod -Uri "http://127.0.0.1:8001/v1/agent/query" `
  -Method Post -ContentType "application/json; charset=utf-8" -Body $body `
  | ConvertTo-Json -Depth 10
```

API 严格返回：

```json
{"answer":"... [S1]","sources":[{"source_id":"S1","chunk_id":"...","source_file":"techqa://...","page_number":1,"quote":"..."}],"confidence":0.74}
```

模糊问题会要求补充产品/版本/错误码；无可靠 Context 的问题返回空 `sources` 和
`confidence: 0`，不调用生成器编造答案。

## 全量导入历史记录

下表记录此前完成的全量导入，服务在线状态需用 `/readyz` 与 collection 查询确认。

| 检查项 | 结果 |
|---|---:|
| 官方全量文档 | 801,998 篇 |
| 全量运行扫描 Chunk | 3,089,056 |
| 本次幂等写入的新向量 | 2,667,445 |
| Qdrant `techqa_full_hash` 当前点数 | 2,826,591 |
| Agent 单元/集成测试 | 34 passed |
| Ruff / MyPy | passed / passed |

2026-09-30 修复复测：测试扩展到 37 项，源码测试不依赖官方数据。
`evaluation.smoke_api` 已改用本 TechQA 数据集的 Streams 4.1.1.2 问题，并验证对应
`techqa://swg21996508` 来源和 `bashrc` 答案；core 和 full API 的三类真实 HTTP 请求全部通过。
全量 Qdrant 已恢复，`/readyz` 返回 200，原 collection 保有 2,826,591 个点。
官方 310 题评测仍需要先下载/导入数据，不能用 fixture 单测结果替代。

当前 `hash` provider 是无需模型下载的可复现离线基线，不是语义 Embedding。在百万级全量库中，
它可能命中词面相近但答案错误的文档；正式部署应改用 `ollama` provider（例如
`nomic-embed-text`）并写入一个全新的 collection，不能把不同 Embedding 混入同一 collection。
程序会检查 `_embedding_id`，模型不匹配时直接失败，避免静默污染索引。

本次修复后对全量 Hash 库重跑了官方全部 310 题：

| 指标 | 全量 Hash 复测 |
|---|---:|
| Hit@5 / Hit@10 | 0.19375 / 0.21875 |
| MRR | 0.19076 |
| 不可回答问题拒答准确率 | 0.54667 |
| 平均评测耗时（检索 + Agent） | 332.28 ms |
| 执行错误 | 0 / 310 |

原始输出见 [full_hash_remediation](evaluation/results/full_hash_remediation/summary.json)。
这些数值说明流程可复现，但全量 Hash 基线的检索质量仍不足；不能用小样例通过代替全量效果。
运行时默认改用 REST，避免本机 Windows/Python 3.14 下实际出现的 gRPC Protobuf 响应解码错误。
评测中的异常题会计入原类别分母，并按失败记 0 分。

## 官方开发集评测

先完成 `core` 或 `full` 导入，再运行：

```powershell
..\.venv\Scripts\python.exe -m evaluation.evaluate
```

评测会遍历官方全部 310 条 `dev_Q_A.json`，输出 Hit@5、Hit@10、MRR、不可回答问题
拒答准确率、平均延迟和逐题记录。它不会把小型测试 fixture 冒充正式评测结果。

以下保留修复前 `core` collection、`hash-sha256-384-v1` 的历史结果；
检索指标保留 Top-10，Agent 回答使用 Top-8。
原始输出保存在 `evaluation/results/core_hash/`：

| 指标 | 结果 |
|---|---:|
| 总问题 / 可回答 / 不可回答 | 310 / 160 / 150 |
| Hit@5 | 0.4875 |
| Hit@10 | 0.5250 |
| MRR | 0.4239 |
| 不可回答拒答准确率 | 0.3733 |
| 平均端到端延迟 | 3178.46 ms |
| 评测错误 | 0 |

这组结果用于暴露离线 fallback 的真实上限，不应包装成生产质量。下一轮应使用语义 Embedding
重建 collection，并在独立验证集上校准相关性阈值；否则词面相近的错误 Context 会同时伤害召回和
拒答准确率。

## 测试

```powershell
..\.venv\Scripts\python.exe -m pytest -q
..\.venv\Scripts\python.exe -m ruff check . --exclude data
..\.venv\Scripts\python.exe -m mypy api agents tools vectorstore models evaluation
```

单元测试使用小型 TechQA 格式 fixture，不下载或索引全量数据；实际命令始终读取官方文件。

## 许可证

代码使用仓库许可证；TechQA 数据本身按归档内的
Community Data License Agreement – Permissive 1.0 单独授权，使用与分发时必须保留该许可。
