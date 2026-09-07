# Step 25 - LangGraph 持久化工作流

本步把现有权限感知检索执行器接入 LangGraph，并使用 Redis checkpointer 保存可恢复状态。

- 工作流分为 `prepare`、`retrieve`、`complete` 三个可检查阶段。
- checkpoint 线程键由服务端已验证的用户 ID 和会话 ID 共同组成，防止跨用户串话。
- Redis checkpoint 使用独立数据库和可配置 TTL，首次运行自动初始化所需索引。
- 仅保留最近 8 轮查询及最多 20 个引用 ID 的结构化摘要，不保存隐藏思维链或无限对话。
- 每个节点仍调用任务活动检查；checkpoint 中的旧图片 ID 不作为权限凭据，使用前必须回源 Java 鉴权。

本步只提交代码和配置模板，不连接或修改本机 Redis。
