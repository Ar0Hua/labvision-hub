# LabVision Hub 本机启动与停止步骤

项目目录：`E:\yu-picture-code`。按以下顺序启动，每个服务已运行时不要重复启动。

## 1. 启动 MySQL

以管理员身份打开 PowerShell：

```powershell
Get-Service MySQL
if ((Get-Service MySQL).Status -ne 'Running') {
    Start-Service MySQL
}
Test-NetConnection 127.0.0.1 -Port 3306
```

`TcpTestSucceeded : True` 表示端口可用。

## 2. 启动 Docker Desktop

从开始菜单打开 Docker Desktop，或在 PowerShell 执行：

```powershell
& 'D:\APP\Docker\Desktop\Docker Desktop.exe'
```

等待左下角显示 `Engine running`。新开 PowerShell，执行：

```powershell
$env:Path = 'D:\APP\Docker\Desktop\resources\bin;' + $env:Path
docker version
```

输出应同时包含 Client 和 Server。后续 Docker 命令在这个终端执行。当前镜像已下载，日常启动不需要重新下载；如果需要拉取镜像，保持 Docker 配置的本机代理 `127.0.0.1:65532` 可用。

## 3. 一条命令启动 Redis 和 Qdrant

```powershell
docker compose -f D:\APP\Docker\labvision\compose.yaml up -d
```

检查：

```powershell
docker compose -f D:\APP\Docker\labvision\compose.yaml ps
docker compose -f D:\APP\Docker\labvision\compose.yaml exec -T redis redis-cli ping
Invoke-RestMethod http://127.0.0.1:6333/readyz
```

Redis 应为 `healthy` 并返回 `PONG`，Qdrant 应通过就绪检查。不要同时启动旧 Windows Redis。

## 4. 在 IDEA 启动 DDD 后端

1. 打开 `E:\yu-picture-code\yu-picture-DDD`。
2. 选择 `YuPictureBackendApplication` 运行配置：Java 11，模块 `yu-picture-backend-ddd`，有效配置文件 `local`。
3. 保留运行配置中的环境变量：`AGENT_INTERNAL_SECRET` 与 `agent-service\.env.local.ps1` 中的实际值相同；`AGENT_SERVICE_BASE_URL=http://127.0.0.1:8000`。
4. 点击运行，等待 Spring Boot 启动完成。

检查：

```powershell
Invoke-RestMethod http://127.0.0.1:8123/api/user/get/login
```

在没有浏览器登录 Cookie 的 PowerShell 中返回“未登录”是正常响应。

## 5. 在 VS Code 启动 Agent

打开 `E:\yu-picture-code\agent-service`，新建 PowerShell 终端：

```powershell
conda activate labvision-agent
cd E:\yu-picture-code\agent-service
Set-ExecutionPolicy -Scope Process Bypass
. .\.env.local.ps1
$env:AGENT_CHECKPOINT_REDIS_URL = 'redis://127.0.0.1:6379/0'
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

保持终端开启。必须在加载本地配置后指定上面的 DB0 地址。

若终端不能识别 `conda`，在 Anaconda Prompt 执行 `conda init powershell`，再重新打开 VS Code。

在另一终端检查：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

应返回 `{"status":"ok"}`。

## 6. 在 VS Code 启动索引 Worker

新建第二个 PowerShell 终端：

```powershell
conda activate labvision-agent
cd E:\yu-picture-code\agent-service
Set-ExecutionPolicy -Scope Process Bypass
. .\.env.local.ps1
$env:AGENT_CHECKPOINT_REDIS_URL = 'redis://127.0.0.1:6379/0'
labvision-index-worker
```

保持终端开启。Worker 持续处理图片索引任务，可能调用 DashScope 产生费用。不要重复启动多个 Worker。

## 7. 启动前端并打开工作台

新建第三个 PowerShell 终端：

```powershell
cd E:\yu-picture-code\yu-picture-frontend
npm run dev
```

保持终端开启。在浏览器打开终端显示的 `Local` 地址，通常为：

- 图库：http://localhost:5173
- Agent 工作台：http://localhost:5173/agent

使用 `localhost`，不要直接替换成 `127.0.0.1`；当前前端可能只监听 IPv6 回环。登录后发送一次检索请求，确认能返回结果。

## 8. 按顺序停止各模块

1. 在 Worker 终端按 `Ctrl+C`，等待退出。
2. 在 Agent 终端按 `Ctrl+C`，等待退出。
3. 在前端终端按 `Ctrl+C`；若询问是否终止批处理，输入 `Y`。
4. 在 IDEA 的 DDD 运行窗口点击红色停止按钮。
5. 在 PowerShell 停止 Redis 和 Qdrant：

```powershell
$env:Path = 'D:\APP\Docker\Desktop\resources\bin;' + $env:Path
docker compose -f D:\APP\Docker\labvision\compose.yaml stop
docker compose -f D:\APP\Docker\labvision\compose.yaml ps -a
```

6. 在 Windows 系统托盘右键 Docker 图标，选择 `Quit Docker Desktop`。仅关闭 Docker 窗口不等于退出引擎。也可以运行：

```powershell
docker desktop stop
```

7. 如果也需要停止 MySQL，在管理员 PowerShell 执行：

```powershell
Stop-Service MySQL
Get-Service MySQL
```

`stop` 会保留 Redis 和 Qdrant 的持久化数据。不要执行 `docker compose down -v` 或删除 `labvision_*` 数据卷。再次启动不需要重新安装依赖、执行数据库迁移或恢复 Qdrant 快照。

## 9. 停止由助手在后台启动的 Agent / Worker

如果看不到对应运行终端，先用以下命令识别本项目的后台进程：

```powershell
$agentProcesses = Get-CimInstance Win32_Process | Where-Object {
    $_.ExecutablePath -eq 'C:\Users\whz\.conda\envs\labvision-agent\python.exe' -and
    $_.CommandLine -match 'uvicorn.*app\.main:app|app\.indexing\.worker'
}
$agentProcesses | Select-Object ProcessId, CommandLine
```

确认是本项目进程后执行（先确保没有正在执行的对话或索引任务）：

```powershell
$agentProcesses | Where-Object { $_.CommandLine -match 'app\.indexing\.worker' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId }
$agentProcesses | Where-Object { $_.CommandLine -match 'uvicorn.*app\.main:app' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId }
```

后台启动日志位于 `D:\APP\Docker\labvision\logs`。停止后可按第 5、6 步改为在 VS Code 终端运行，之后使用 `Ctrl+C` 正常停止。
