# Agent 任务持久化基础

新增 agent_task 表、领域实体、Mapper 和对外状态 DTO。
提交用户消息时，在同一 Spring 事务中先保存消息，再创建 PENDING/QUEUED 任务并返回 taskId。
新增 GET /api/agent/tasks/{id}；读取任务时通过所属会话验证当前用户，响应不包含内部 userId。

迁移脚本 V004__agent_task.sql 需在 V003 后执行。本次没有修改实际数据库。
单元测试验证正常建任务、建任务失败、非法或不存在的任务，以及读取时的会话归属检查。
本步骤完成后全部 Agent 回归测试共 12 项通过。

当前任务只是可持久化状态记录，尚无 worker、状态流转、SSE、取消、重试和 checkpoint。
事务回滚需要在真实 Spring + MySQL 集成测试中确认；单元测试只能验证失败会抛出异常。
