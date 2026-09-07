# 持久任务事件与断线补拉

新增 agent_task_event 表，以自增事件 ID 保存公开阶段事件。事件类型使用服务端允许列表，payload 必须是有效 JSON 且不超过 65535 字符。
创建任务时写入 queued 状态事件。

新增 GET /api/agent/tasks/{id}/events?afterEventId=...&limit=...。
接口先校验任务所属会话，随后按递增 ID 返回最多 200 个事件；事件 ID 对外转为字符串，避免浏览器丢失 bigint 精度。
客户端可保存最后 eventId，在刷新或断线后增量补拉。

V006__agent_task_event.sql 需在 V004 后执行，本次未修改实际数据库。
目前是持久事件和补拉 API，真正的 text/event-stream SSE 长连接在下一步骤实现。
