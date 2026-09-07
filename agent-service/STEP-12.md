# Java 内部任务网关

新增由 Bearer 短期任务令牌保护的内部接口：

- GET /api/agent/internal/tasks/{id}/context
- POST /api/agent/internal/tasks/{id}/events
- POST /api/agent/internal/tasks/{id}/state

读取上下文时同时核对令牌、任务、输入消息、会话、用户和空间关系，并重新执行当前空间权限校验。
上下文只返回任务所需查询和标识，不返回 Cookie、永久图片 URL 或用户密码。
任务状态仅允许 PENDING -> RUNNING -> SUCCEEDED/FAILED，使用条件更新避免并发覆盖；状态与公开事件在同一事务保存。

当前尚未实现 Java 主动向 Python 派发任务，内部令牌也不会暴露给浏览器。
