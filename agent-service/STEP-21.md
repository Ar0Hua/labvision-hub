# 第 21 步：图片索引 outbox

## 本步完成

- 新增迁移 `V007__picture_index_outbox.sql`，保存 `UPSERT/DELETE`、重试次数、可用时间、锁定时间和安全错误摘要。
- MySQL 触发器覆盖图片新增、影响索引的元数据更新、空间迁移、公共审核变化、逻辑删除与物理删除。
- 公共图片未审核通过时生成 `DELETE`；空间图片只要未删除即可生成 `UPSERT`，权限仍在查询和回源阶段复核。
- 历史有效图片通过 `bootstrap:{pictureId}` 幂等补入 outbox，重复执行不会重复生成初始化事件。
- 增加 Java 实体与 Mapper，为下一步内部 claim/ack 接口提供访问层。

## 顺序与一致性

outbox ID 是同一图片变更的顺序依据。worker 必须按 ID 处理，并在写 Qdrant 后才确认成功；较新的事件最终覆盖较旧索引状态。

## 尚未完成

- 本迁移尚未在用户数据库执行。
- 下一步实现带租约的 claim/success/failure 内部接口及 Python worker。
