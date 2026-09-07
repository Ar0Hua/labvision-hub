# 会话归属持久化基础

以 MySQL agent_conversation 替换 Redis 24 小时归属信息，每次查询核验当前用户和 ACTIVE 状态。
新增增量脚本 yu-picture-DDD/sql/agent/V001__agent_conversation.sql。
本次仅开发代码，没有执行迁移；使用新会话接口前须手动建表，未建表时请求将失败。
旧 Redis 会话不会自动迁移，需要创建新会话。

单元测试使用模拟 Mapper，验证创建失败、归属变化、关闭、缺失、非法 ID 和未登录情况。
真实 MySQL 迁移与重启恢复尚未集成验证。
待开发：消息、任务、checkpoint、内部服务签名、模型接入。本次不是完整会话恢复能力。
