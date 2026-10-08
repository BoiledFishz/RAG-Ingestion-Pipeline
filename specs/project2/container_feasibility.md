# Chap14 容器可行性

实际本机盘点；尚未构建或运行容器。

- .rag_data/techqa_full.sqlite：4.273 GiB
- .rag_data/techqa_semantic：22.076 GiB
- .rag_data/models/minilm：0.085 GiB
- .rag_data/project2_runtime：0.000 GiB

全量索引3089056 Chunk；工作区盘剩余1154.475 GiB。Docker CLI=C:\Program Files\Docker\Docker\resources\bin\docker.EXE，daemon可用=False。

全文/FAISS/元数据与嵌入模型使用本机只读挂载，不复制到镜像；避免309万Chunk的大体积构建上下文和双份磁盘。状态卷独立保留，停止不删除。生成模型沿用本机Ollama，不能拉模型、拉远端镜像或安装系统依赖。冷启动需同时容纳FAISS、SQLite页缓存、MiniLM、生成模型和容器内存；盘点不能代替真实就绪/状态恢复门禁。

停止原因：Docker daemon不可用；不得安装/启动外部服务或用配置代替真实门禁
