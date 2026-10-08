# Chap14 构建资源方案（等待授权）

2026-10-07。Docker Engine 已真实就绪；当前缓存只有 pgvector 与 Qdrant 镜像。离线运行 pgvector 的 `command -v python3` 返回 127。工作区没有 Linux wheel / deb / Python 基础镜像，Windows 虚拟环境不能作为 Linux 镜像运行环境。

为了构建课程要求的实际 API 容器，拟仅下载：

- Docker 官方 `python:3.12-slim`，下载后记录镜像 digest 并固定构建引用。
- API 所需 Linux Python 依赖：FastAPI、Uvicorn、Pydantic、HTTPX，以及现有 RAG 所需 ijson、qdrant-client、langchain-text-splitters、PyYAML、python-dotenv、NumPy、FAISS、Transformers、CPU PyTorch 2.8.0 与它们的依赖。下载后记录版本及 wheel SHA256，用本地 wheelhouse 离线安装进镜像。

范围是 Docker Hub / PyPI / PyTorch 官方 CPU 仓库的免费构建材料；不使用付费 API，不安装 Windows 系统软件，不下载模型或数据，不操作云平台。数据与现有 MiniLM 全量索引只读挂载；沿用本机 Ollama，状态卷保留。

新增版本化容器入口只适配 Linux Python 路径和本机 Ollama 的网络地址，默认 MultiAgent 与冻结 v0 不改。预算仍 19 / 6 / 90，启动加载与预热在就绪前完成。干净构建、实际组合请求、日志诊断、保留卷后重启恢复都需实测，配置文件不算通过。

此前用户明确禁止在线资源，因此在新的下载授权前不拉取镜像、不下载依赖。若不批准，Chap14 保留构建资源阻塞、Chap15 不推进。

证据：docker_after_windows_restart.json（本地镜像、真实 Python 检查）。下载大小需实际解析依赖后报告，当前不能承诺精确大小；CPU PyTorch 等材料可能达数百 MB。
