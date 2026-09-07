# 第 19 步：DashScope 向量、Qdrant 与 RRF 融合

## 本步完成

- 使用 DashScope OpenAI 兼容 `/embeddings` 生成 `text-embedding-v4` 查询向量，维度可配置。
- 使用 Qdrant `/collections/{collection}/points/query` 查询向量候选，并强制带 `scopeKey=public` 或 `scopeKey=space:{id}` 过滤。
- Qdrant payload 只接受字符串 `pictureId`；候选必须再调用 Java details 工具回源鉴权，未通过的 ID 不进入融合或引用。
- 使用既有 RRF 将 MySQL 关键词通道与已授权向量通道融合，保持字符串 ID 精度。
- DashScope/Qdrant 缺失或故障时静默降级到关键词通道，不让基础检索不可用。

官方接口依据：

- DashScope embedding：<https://help.aliyun.com/en/model-studio/embedding-interfaces-compatible-with-openai>
- Qdrant query points：<https://api.qdrant.tech/api-reference/search/query-points>

## 尚未完成

- 尚未创建 Qdrant collection、payload index 或历史图片索引；因此未部署前向量通道不会产生结果。
- 下一步实现可重放的图片索引任务/outbox 与索引 worker。
