# 第 22 步：索引任务租约与确认接口

## 本步完成

- 新增 V008 租约字段和 `(id,status,leaseToken)` 索引。
- 新增 60 秒、独立 purpose 的 HMAC Worker 令牌，不能冒充用户任务令牌。
- `POST /api/agent/internal/index/jobs/claim` 使用数据库行锁与 `SKIP LOCKED` 并发领取任务，过期 5 分钟租约可被恢复。
- claim 返回图片当前快照而非历史事件快照；已删除或不再公开的图片统一转为 `DELETE`。
- ack 必须匹配 job ID 和 leaseToken；失败按尝试次数指数退避，错误摘要去除换行并限制长度。

## 尚未完成

- V007/V008 尚未执行。
- 下一步实现 Python Worker 的短期令牌签发、claim、DashScope embedding、Qdrant upsert/delete 和 ack 循环。
