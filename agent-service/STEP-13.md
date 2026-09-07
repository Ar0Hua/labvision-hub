# 第 13 步：Java 任务异步分发

## 本步完成

- 新建任务和失败/取消后的重试会在数据库事务提交成功后发布分发事件。
- 分发监听器使用独立异步线程调用 Python Agent 服务，HTTP 请求携带第 10 步定义的短期 HMAC 上下文令牌。
- 分发前再次读取任务和会话，仅允许仍为 `PENDING`、会话仍有效且用户关系一致的任务离开 Java 服务。
- 连接失败会把仍为 `PENDING` 的任务条件更新为 `FAILED / DISPATCH_FAILED`，并持久化安全的错误事件，避免任务永久停留在队列中。
- HTTP 连接和读取超时均可由环境变量配置，默认 Agent 地址仅指向本机。

## 配置

- 仓库示例见 `yu-picture-DDD/src/main/resources/application-agent.example.yml`；实际值使用环境变量或合并到本机未入库配置。
- `AGENT_INTERNAL_SECRET`：Java/Python 共享，至少 32 个字符，不得提交仓库。
- `AGENT_SERVICE_BASE_URL`：默认 `http://127.0.0.1:8000`。
- `AGENT_SERVICE_CONNECT_TIMEOUT_MS`：默认 2000。
- `AGENT_SERVICE_READ_TIMEOUT_MS`：默认 5000。

## 安全边界

- 浏览器仍然只获取任务 ID，内部令牌不会进入前端响应。
- 异步动作在事务提交后执行，不会向尚未落库的任务发起请求。
- 取消与分发竞争时，非 `PENDING` 任务会被跳过。

## 尚未完成

- Python 的 `/internal/tasks/{taskId}/run` 接口和实际执行器将在下一步实现。
- 本步未部署服务，也未执行数据库迁移。
