# Step 28 - Agent 会话列表契约

本步为前端工作台补齐同域 Java 会话列表接口。

- `GET /api/agent/conversations` 只按当前登录用户查询。
- 最多返回最近更新的 50 个会话，避免无界加载。
- 对外 VO 不包含内部 userId，只返回会话、空间、状态和时间字段。
- 会话 ID 与空间 ID 均以字符串返回，避免浏览器丢失 bigint 精度。
