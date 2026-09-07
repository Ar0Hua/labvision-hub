# SSE 实时任务事件

GET /api/agent/tasks/{id}/events 现在返回 text/event-stream。
连接返回前同步校验任务归属；后台每 500ms 增量读取持久事件，发送事件 id、类型和 JSON 数据。
支持标准 Last-Event-ID，也支持 afterEventId 查询参数。Last-Event-ID 优先，断线后可从持久事件继续。
每次连接最长 30 秒，服务端工作循环最多 25 秒，客户端按 reconnectTime 自动重连。

原 JSON 补拉接口调整为 /api/agent/tasks/{id}/events/history。
当前实现采用数据库短轮询，适合开发和低并发；生产阶段应通过 Redis Streams/通知机制减少空查询，并配置受控线程池、连接数和限流。
