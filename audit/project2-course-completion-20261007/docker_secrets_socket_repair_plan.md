# Docker 下一处运行 socket 修复方案（待批准）

2026-10-07。已批准的 Docker/run 备份、重建与重启已执行；该处原错误已移除，但引擎在下一个服务启动步骤失败。

实际 backend.error.json 指向 `C:/Users/zacha/AppData/Local/docker-secrets-engine/engine.sock`：系统无法访问/移除该文件。只读清单显示该目录仅一个 0 字节 Archive/ReparsePoint 的 IPC socket，不含配置或数据文件。

拟停止现有 Docker Desktop 与其 backend；确认源目录解析后正是上述普通目录、备份不存在且只含 engine.sock；将整个目录原样改名为 `docker-secrets-engine.course-backup-20261007`，重建空同名目录，再隐藏启动现有 Desktop。备份保留，不删除文件，不改数据卷、WSL 磁盘、镜像、模型、密钥存储或设置，不安装/下载。若清单不符立即停止。

证据：docker_ready_after_directory_repair.json（20秒超时）、docker_backend_after_directory_repair.json（错误原字节与SHA256）。本操作在仓库外，等待用户授权；若出现其他路径的新错误，不扩大修复范围。
