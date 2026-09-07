# 第 14 步：Python 受保护任务接收与回调闭环

## 本步完成

- 新增 `POST /internal/tasks/{taskId}/run`，只接受 Java 签发且任务范围匹配的 Bearer 令牌。
- 使用有界、线程安全的进程内登记表拒绝同一签名分发的重复执行；新重试产生的新令牌仍可进入队列。
- 后台执行前通过 Java 内部网关重新获取任务上下文，并逐项比对任务、会话、用户和空间范围。
- 封装 Java 回调客户端，统一回写 `RUNNING / SUCCEEDED / FAILED` 状态和增量事件，严格检查 Java 响应码。
- 默认执行器明确返回 `EXECUTOR_UNAVAILABLE`，不会把占位文字伪装成真实检索结果。

## 配置兼容

- Python 新部署统一读取 `AGENT_INTERNAL_SECRET`，与 Java 同名、同值。
- 暂时兼容旧变量 `AGENT_SERVICE_SECRET`，便于平滑迁移。
- `JAVA_REQUEST_TIMEOUT_SECONDS` 默认 10 秒。

## 尚未完成

- 当前队列只适合单进程开发；生产环境需要持久队列或 outbox 消费器。
- 下一步接入真实的权限安全检索执行器；本步未部署服务、未调用 DashScope 或 Qdrant。
