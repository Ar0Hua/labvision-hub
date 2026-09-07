# 第 18 步：外部索引候选回源鉴权

## 本步完成

- 新增内部接口 `POST /api/agent/internal/tasks/{taskId}/pictures/details`，接收最多 20 个图片 ID。
- 用户与会话只能取自短期签名任务上下文，接口不接受客户端指定 userId、spaceId 或 conversationId。
- 每个候选复用 `AgentPictureService.details` 回查 MySQL，并重新校验会话归属、会话空间、当前空间查看权限或公共图库审核状态。
- 返回仍然只有必要元数据，不含永久 COS URL。

## 目的

Qdrant 是检索索引而不是权限事实源。即使索引数据延迟、陈旧或被错误写入，候选图片也必须通过本接口逐项复核后才能进入回答或发送给云端模型。

## 尚未完成

- 下一步实现 DashScope 文本向量与 Qdrant 查询适配，并把回源通过的结果加入 RRF。
- 本步未部署服务、未安装或启动 Qdrant。
