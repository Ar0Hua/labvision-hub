# 第 23 步：可重放图片索引 Worker

## 本步完成

- 新增 `labvision-index-worker`，支持常驻轮询和 `--once` 单批运行。
- 每次 claim/ack 都生成新的 60 秒 Worker HMAC 令牌，不使用长期裸密钥作为 Bearer 值。
- UPSERT 将图片名称、简介、分类和标签组合为受限文本，通过 DashScope embedding 后写入 Qdrant。
- Qdrant point ID 使用图片 bigint，payload 中 `pictureId` 保持字符串，并写入权限范围 `scopeKey`。
- DELETE 等待 Qdrant 确认后再 ack；任何 embedding/Qdrant 异常都会 failure ack，交由 Java 指数退避重试。
- 错误回传只包含异常类型，不上传 URL、密钥或第三方响应正文。

## 尚未完成

- V007/V008、Qdrant collection 尚未实际初始化，Worker 未启动。
- 下一步增加任务取消传播、多轮 checkpoint 和 LangGraph 工作流。
