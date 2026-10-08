# Docker 本地启动修复方案（待用户批准）

2026-10-07。已获得的授权仅为停止并重启现有 Docker Desktop，已实际执行。重启后的本地引擎仍不可连接，新后端日志仍在初始化 dockerInference 时报告无法移除运行 socket。没有安装、下载或更改设置。

拟执行的最小修复：

1. 核验并停止现有 Docker Desktop/后端进程；不停止其他程序。
2. 核验绝对源路径为 `C:\Users\zacha\AppData\Local\Docker\run`，它为普通目录，包含三个运行 socket/reparse 文件。
3. 将该目录原样改名备份为 `C:\Users\zacha\AppData\Local\Docker\run.course-backup-20261007`；若目标已存在则停止，不覆盖。使用 PowerShell 原生目录移动，不递归删除、不跟随 socket 目标。
4. 重建空 `run` 目录，隐藏启动已有 Docker Desktop，执行有超时的本地引擎就绪检查。
5. 保留备份和原始/重启错误记录。失败则停止，另行报告；不反复操作，不升级/安装/下载。

范围与风险：只涉及仓库外的 Docker 临时 IPC 运行目录，可能使当前 Desktop 会话的 IPC 端点失效。Docker 当下未能启动；数据卷、WSL 虚拟磁盘、镜像/模型存储、用户配置和凭证目录均不修改。此方案须获得用户明确批准后执行，当前未执行。
