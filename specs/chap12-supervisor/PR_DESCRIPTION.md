# Chap12：Supervisor–Worker 骨架（TechQA 随机 150 题样本）

## 内容
- 新增 `enterprise-ai-agent/agents/chap12/`：Supervisor、确定性 planner、RAG Worker（复用 Project 1 `RAGAgent`）、Database Query Worker（参数化只读模板）、预算、Contract。
- 新增 `api/chap12_main.py`（`POST /v1/chap12/analyze`）和 `tools/sample_retriever.py`。
- 新增样本构建脚本和对照评测脚本：`evaluation/chap12_build_sample.py`、`evaluation/chap12_compare.py`。
- 新增规格文档：`specs/chap12-supervisor/`（spec、tasks、comparison）。
- 没有修改任何已有文件：Project 1、旧的 `api.main`、`specs/project2` 都保持原样。

## 实际运行的命令与结果（本机 Linux，Python 3.12.15）
```
cd enterprise-ai-agent; export PYTHONPATH=../src:.
python -m evaluation.chap12_build_sample            # 150 题, 6612 篇, index sha256 ea27055d…
python -m pytest tests/chap12 -q                    # 91 passed
python -m pytest tests -q --ignore=tests/project2   # 143 passed（其中 52 个为已有测试，无回归）
ruff check agents/chap12 api/chap12_main.py tools/sample_retriever.py evaluation/chap12_*.py tests/chap12   # All checks passed
mypy --python-version 3.12 agents/chap12 api/chap12_main.py tools/sample_retriever.py evaluation/chap12_*.py
    # 新文件 0 个错误；唯一的报错是已有的 src/rag/techqa/claims.py:25 多余 type: ignore
AGENT_PROFILE=offline python -m evaluation.chap12_compare --output evaluation/chap12/results/offline_20261011     # v1
python -m evaluation.chap12_build_sample --seed 20261012 ... --exclude-manifest ...   # 独立调参集
python -m evaluation.chap12_build_dense --index ...                                  # 样本 MiniLM 向量
python -m evaluation.chap12_retrieval_tune --split tune                              # 方案选择 + 阈值
AGENT_PROFILE=offline python -m evaluation.chap12_compare --output evaluation/chap12/results/offline_v2_20261011  # v2
```
注：mypy 使用 `--python-version 3.12`，因为在 pyproject 设定的 3.11 下，numpy 的类型存根会报语法错误。

## 待运行（需要本机的 Ollama）
```powershell
cd enterprise-ai-agent; $env:PYTHONPATH="../src;."; $env:AGENT_PROFILE="ollama"
../.venv312/Scripts/python.exe -m evaluation.chap12_compare --output evaluation/chap12/results/ollama_run1
# 中断后加 --resume 续跑；也可设 $env:CHAP12_RERANKER="minilm" 与默认 nomic 重排对比
```

## 已知限制
见 `specs/chap12-supervisor/improvements.md`。要点：尚未用真实模型运行；v2 的拒答从 16/27 降到 8/27；推断产品约 1/4 与金标文档不一致；token 数为 null；规格尚未人工审阅。

未 push，未创建 PR，需要你本人审阅后再操作。
