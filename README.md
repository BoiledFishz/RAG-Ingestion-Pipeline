# AWS Support Production RAG Backend

一条面向生产环境的 PDF/Markdown → 清洗 → OCR 兜底 → 递归切片 → LLM 上下文增强 →
异步 Embedding → Qdrant 幂等写入流水线，以及可通过 HTTP 查询的 Dense + BM25 + RRF
混合检索、重排、受限 Context、引用校验和拒答链路。

> `data/sample` 是可公开复现的合成 AWS 支持文档，不是 AWS 官方文档。生产环境应替换为
> 经批准的数据源。

## 架构

```mermaid
flowchart LR
    A["PDF / Markdown"] --> B["原生文本解析"]
    B --> C{"页面文本是否足够?"}
    C -- "否" --> D["PyMuPDF 渲染 + Tesseract OCR"]
    C -- "是" --> E["clean_text"]
    D --> E
    E --> F["RecursiveCharacterTextSplitter"]
    F --> G["SHA-256 chunk_hash"]
    G --> H{"Qdrant 中已存在?"}
    H -- "是" --> I["跳过摘要与 Embedding"]
    H -- "否" --> J["Ollama 一句话 context_summary"]
    J --> K["异步批量 Embedding"]
    K --> L["Qdrant Upsert"]
    L --> M["Dense + BM25"]
    M --> N["RRF + Reranker + Context Builder"]
```

关键保证：

- PDF 每页先用 `pypdf` 抽取；文本低于阈值时自动用 PyMuPDF 以 300 DPI 渲染并调用
  Tesseract。单页 OCR 失败只记 WARNING，不中断其他页或文件。
- 使用 LangChain `RecursiveCharacterTextSplitter`，分隔符按段落、行、句子、词逐级回退；
  没有固定宽度硬切逻辑。
- 每个 Chunk 强制包含 `source_file`、`page_number`、文本 SHA-256 `chunk_hash` 和一句话
  `context_summary`。LLM 暂时不可用时记录 `summary_fallback=true` 并注入抽取式兜底摘要。
- `chunk_hash` 库内查询发生在摘要和 Embedding 之前；重复运行不会产生重复向量，也不会
  重复产生模型费用。
- 摘要与 Embedding 都是异步、有限并发、批量处理；所有核心函数有类型提示，生产路径只用
  `logging`，没有 `print()`。

## Retrieval 与 Generation 架构

```mermaid
flowchart LR
    Q["POST /v1/rag/query"] --> SF["强制安全过滤<br/>status=published"]
    SF --> D["Dense Top-30"]
    SF --> S["BM25 Top-30"]
    D --> RRF["RRF(k=60)"]
    S --> RRF
    RRF --> DD["按 chunk_id 去重"]
    DD --> RR["Reranker Top-20"]
    RR --> F["Final Top-5"]
    F --> P["可选 Parent Node"]
    P --> C["Context Budget<br/>每文档最多 2 块"]
    C --> L["LLM"]
    L --> V{"[S1] 引用有效?"}
    V -- "是" --> A["Answer + Citations"]
    V -- "否" --> RT["重试一次"]
    RT --> V2{"仍然无效?"}
    V2 -- "是" --> X["拒答"]
    V2 -- "否" --> A
```

完整数据流为：

```text
PDF/Markdown → Page → Recursive Chunk → chunk_id/chunk_hash → Qdrant
User Query → 强制 Metadata Filter → Dense 与 BM25 并行 → RRF → Reranker
→ Token-budget Context → Ollama → Citation Validation → Answer/Refusal
```

支持 `mode=dense`、`mode=sparse` 和 `mode=hybrid`。用户可过滤 `source_file`、
`document_type`、`language`；`status=published` 由系统强制注入，用户提交
`status=draft` 也不能覆盖。Dense、Sparse 与 Reranker 通过独立接口注入。

### RRF 公式

本项目手写 Reciprocal Rank Fusion，而不是调用黑盒框架：

```text
RRF_score(d) = Σ 1 / (k + rank_r(d))
               r∈retrieval_lists
```

生产默认 `k=60`。同一 `chunk_id` 在 Dense 与 BM25 中出现时只保留一次，同时记录
`dense_rank`、`sparse_rank`、`fusion_rank` 和 `retrieval_sources`。Dense 或 BM25
单路异常时记录日志并使用另一路返回。

### Reranker 与降级

本地 `LexicalReranker` 是可解释的 `BaseReranker` Adapter，仅接收检索得到的最多 20 个
候选，并同时使用 Query、Chunk 正文与 `context_summary`。超时或异常时自动恢复 RRF/Dense
原排序；候选为空时不会调用 Reranker。结果同时保留 `retrieval_rank`、
`retrieval_score`、`rerank_rank` 和 `rerank_score`。

## 快速开始

核心流水线需要 Python 3.11+。Windows 上运行完整 Ragas 评测推荐 Python 3.12；更新的
Python 版本可能因 `scikit-network` 暂无对应预编译 wheel 而要求本机安装 C++ 编译工具。
Ollama 是默认的免费本地模型服务；OCR 还需要操作系统中已安装
[Tesseract](https://github.com/tesseract-ocr/tesseract)。

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -e ".[dev,eval,api]"

ollama pull llama3.2:3b
ollama pull nomic-embed-text
cp .env.example .env
python main.py data/sample
```

离线/CI 冒烟运行可使用确定性的特征哈希向量和抽取式摘要；它用于复现测试，不建议替代生产
语义模型：

```bash
python main.py data/sample --summary-provider extractive --embedding-provider hash
```

常用环境变量见 [.env.example](.env.example)。若使用远程 Qdrant，可直接实例化
`QdrantVectorStore(url=..., api_key=...)`；默认使用 `.rag_data/qdrant` 本地持久化模式。

### 启动查询 API

先使用与查询相同的 Embedding 模型执行 ingestion，再启动服务：

```powershell
$env:QDRANT_PATH = ".rag_data/qdrant"
$env:QDRANT_COLLECTION = "aws_support"
$env:RETRIEVAL_MODE = "hybrid"
$env:EMBEDDING_PROVIDER = "ollama"

rag-api
```

请求：

```http
POST /v1/rag/query
Content-Type: application/json

{
  "query": "Which policy layers should be checked for S3 403 AccessDenied?",
  "mode": "hybrid",
  "filters": {
    "language": "en",
    "document_type": "markdown"
  }
}
```

一次成功回答示例：

```json
{
  "answer": "Review identity policies, the bucket policy, SCPs, permissions boundaries, endpoint policies, KMS policy, and ownership controls [S1].",
  "citations": [
    {
      "source_id": "S1",
      "chunk_id": "2cf...9ab",
      "source_file": "s3_support_runbook.md",
      "page_number": 1
    }
  ],
  "retrieval": {
    "mode": "hybrid",
    "dense_candidates": 28,
    "sparse_candidates": 6,
    "reranked_candidates": 20,
    "final_chunks": 2,
    "context_tokens": 476,
    "reranker_fallback": false
  },
  "refused": false,
  "refusal_reason": null
}
```

知识库无法回答时不会调用 LLM，或在 Citation 修复失败后拒答：

```json
{
  "answer": "知识库无法回答该问题。",
  "citations": [],
  "retrieval": {
    "mode": "hybrid",
    "dense_candidates": 28,
    "sparse_candidates": 0,
    "reranked_candidates": 20,
    "final_chunks": 0,
    "context_tokens": 0,
    "reranker_fallback": false
  },
  "refused": true,
  "refusal_reason": "below_relevance_threshold"
}
```

## 测试与黄金集评测

```bash
pytest
python evals/evaluate_retriever.py \
  --data-dir data/my_docs \
  --golden evals/my_docs_golden_dataset.json \
  --output evals/my_docs_results.json \
  --chunk-sizes 256 512 \
  --top-k 3
```

合成评测语料位于 `data/my_docs/aws_support_synthetic.md`，配套黄金集位于
`evals/my_docs_golden_dataset.json`，包含 5 个 `Question / Ground Truth / Reference
Evidence` 对，覆盖 S3、EC2、Lambda、RDS Proxy 和 CloudFront。评测先完整运行 ingestion，
再执行混合召回；随后用 Ragas
`IDBasedContextRecall` 比较召回的 `chunk_hash` 和证据所在 Chunk 的哈希，无需付费 API 或
LLM-as-a-judge。明细写入 `evals/my_docs_results.json`。

| Chunk Size | Overlap | Chunk 数 | Ragas Context Recall@3 | 说明 |
|---:|---:|---:|---:|---|
| 256 | 32 | 17 | 1.00 | 五题所需证据均在 Recall@3 中命中 |
| 512 | 64 | 8 | 1.00 | 保持完整召回，同时显著减少向量数量 |

生产默认推荐 **512 字符 + 64 字符 overlap**：两种参数的 Recall@3 均为 1.00，但 512 将向量数
从 17 降至 8，减少约 53% 的首次 Embedding、索引存储和摘要请求。AWS 故障排查步骤经常需要
同一段中的“症状、原因、操作”共同出现，512 也更不容易拆散条件与结论。若真实语料以短 FAQ
为主，应以自己的黄金集重新选择参数，而不是照搬默认值。

### 混合格式压力测试

`data/aws_support_test_corpus` 是另一套合成集成测试语料，包含 Markdown、双页文本 PDF、双页
扫描 PDF、空 Markdown 和故意损坏的 PDF。Windows 上安装 Tesseract 后可运行完整 OCR 与
Ragas 验证：

```powershell
$env:Path = "C:\Program Files\Tesseract-OCR;" + $env:Path

.\.venv312\Scripts\python.exe evals\evaluate_retriever.py `
  --data-dir data\aws_support_test_corpus\data `
  --golden evals\aws_support_test_corpus_golden.json `
  --database-root .rag_data\corpus-eval `
  --output evals\aws_support_test_corpus_results.json `
  --chunk-sizes 256 512 `
  --top-k 3
```

集成验证结果：4 个有效文档成功解析，空文件和损坏 PDF 被安全跳过；扫描 PDF 的两页触发 OCR。
首次运行写入 28 个 512-size Chunk，第二次运行全部按 `chunk_hash` 跳过。每个 Chunk 均包含
`source_file`、`page_number`、`chunk_hash` 和 `context_summary`。

| Chunk Size | Overlap | Chunk 数 | Ragas Context Recall@3 |
|---:|---:|---:|---:|
| 256 | 32 | 59 | 0.50 |
| 512 | 64 | 28 | 0.40 |

该压力测试使用确定性的 Hash Embedding，因此分数用于离线回归，不代表生产语义检索质量。256
在此语料上召回更高，但向量数约为 512 的两倍；上线前应改用 Ollama 或生产 Embedding 模型，
再以真实支持问题重新评测参数。

### 15 题 Retriever 对比

`evals/retrieval_golden_dataset.json` 包含 5 条语义问题、4 条错误码/API/产品名问题、
3 条 Metadata Filter 问题和 3 条不可回答问题。运行：

```powershell
$env:TESSERACT_CMD = "C:\Program Files\Tesseract-OCR\tesseract.exe"
.\.venv\Scripts\python.exe evals\evaluate_retrieval_modes.py
```

| 模式 | Recall@5 | Recall@10 | MRR | Context Precision | 平均延迟 | 拒答准确率 |
|---|---:|---:|---:|---:|---:|---:|
| Dense | 1.000 | 1.000 | 0.861 | 0.767 | 1.88 ms | 1.000 |
| Dense + Rerank | 1.000 | 1.000 | 0.958 | 0.800 | 2.45 ms | 1.000 |
| Hybrid + Rerank | 1.000 | 1.000 | 1.000 | 0.800 | 2.85 ms | 1.000 |

基于该测试集校准的相关性阈值分别为 Dense+Rerank `0.498`、Sparse+Rerank `0.500`
和 Hybrid+Rerank `0.545`。最终推荐 **candidate_k=30、rerank_k=20、final_k=5**：
30 个双路候选为错误码和语义表达保留足够覆盖，20 个精排输入限制成本与敏感数据暴露，
最终 5 个结果再经每文档最多 2 块和 8000-token Context Budget 约束。Hybrid + Rerank
在只增加约 1 ms 本地延迟的情况下取得最高 MRR，因此作为默认模式。

## 目录

```text
.
├── main.py                       # 作业要求的主入口
├── utils.py                      # 作业要求的解析/清洗兼容入口
├── test_pipeline.py              # 作业要求的两项核心单测
├── src/rag/
│   ├── ingestion/                # 解析、OCR、切片、摘要、Embedding、Qdrant
│   ├── retrieval/                # dense、BM25、filter、RRF、reranker、context
│   ├── generation/               # prompts 与 Ollama generator
│   └── api/                      # 可选 FastAPI route factory
├── tests/                        # 检索、重排、上下文、幂等测试
├── evals/                        # 5 题黄金集与 Ragas 脚本
├── data/sample/                  # 合成可复现数据
└── pyproject.toml
```

## 生产注意事项

- Tesseract 是独立系统程序；容器镜像中应固定它和语言包的版本。`OCR_LANGUAGES` 可设为
  `eng+chi_sim`，`TESSERACT_CMD` 可显式指向可执行文件。
- 默认 Ollama API 没有鉴权。跨主机部署时应置于私网并通过带 TLS/鉴权的网关访问。
- 本地 Qdrant 适合单机开发；多副本生产环境应使用 Qdrant Server/Cloud，并配置备份、TLS、
  API key、索引监控和磁盘水位告警。
- 当前 BM25 索引在进程启动时从 payload 重建，适合中小型知识库。大规模部署应换成 OpenSearch
  或 Qdrant 原生 sparse vectors，同时保留 `Retriever` 接口和 RRF 层。
- 修改 embedding 模型会改变向量维度和空间，应写入新的 collection 并完成离线验证后原子切换，
  不要把不同模型的向量写入同一 collection。
