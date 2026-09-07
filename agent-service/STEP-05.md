# Agent 消息持久化

新增 agent_message 表、领域实体和 Mapper，保存用户可见消息。
提供 POST/GET /api/agent/conversations/{id}/messages，写入和读取前均检查当前用户的会话归属。
用户消息去除首尾空白，限制为 1～8000 个字符；角色由服务端固定为 USER，客户端不能伪造 ASSISTANT 或 SYSTEM。
模型隐藏思维链不进入消息表。

迁移脚本 V003__agent_message.sql 需要在 V001、V002 后手动执行。本次没有修改实际数据库。
当前列表接口尚未分页，只适合早期短会话；在接入模型前需补充分页和安全的响应 DTO。
模型回复、引用、任务状态和 token 用量尚未实现。
