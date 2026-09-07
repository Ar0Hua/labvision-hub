# 任务取消与重试

新增 POST /api/agent/tasks/{id}/cancel 和 /resume。
取消仅接受 PENDING/RUNNING，重复取消保持幂等；重试仅接受 FAILED/CANCELLED，并递增 retryCount、清除错误、重新进入 PENDING/QUEUED。
状态更新在 SQL 条件中限制旧状态，用受影响行数识别并发状态变化。

V005__task_retry.sql 需在 V004 后执行，本次未修改实际数据库。
当前取消状态已持久化，但尚未连接执行 worker 的协作取消信号；resume 也尚未从 checkpoint 恢复，后续接入 Python Agent 后补全。
