# LabVision Agent 部署 Runbook

本文只描述部署步骤，本次开发没有执行这些操作。

## 1. 上线前

1. 备份目标 MySQL，并确认当前 DDD 后端版本和 `picture` 表结构。
2. 按顺序人工审核并执行 `yu-picture-DDD/sql/agent/V001` 至 `V008`；每步核对表、索引和触发器。
3. 准备 Redis 8 checkpoint 实例和 Qdrant；二者使用独立账号、网络访问控制和持久卷。
4. 创建至少 32 字节的随机 `AGENT_INTERNAL_SECRET`，Java 与 Python 使用相同值，不写入仓库。
5. 配置 DashScope API Key、地域匹配的 Base URL、聊天/视觉/embedding 模型和 COS 参数。

## 2. 启动顺序

1. MySQL、Redis、Qdrant。
2. 在 `agent-service` 安装 `.[retrieval,agent]`，执行 `labvision-qdrant-init`。
3. 启动 `labvision-index-worker`，观察 outbox 租约、失败重试和索引延迟。
4. 启动 FastAPI/uvicorn，检查 `/health` 和 `/metrics`。
5. 合并 `application-agent.example.yml` 到 Java 的未入库配置后启动 DDD 后端。
6. 设置可选 `VITE_API_BASE_URL`，构建并发布 Vue 前端。

## 3. 冒烟检查

- 未登录访问会话、任务和 SSE 均被拒绝。
- 公共会话只能引用已审核公共图片；空间会话只能引用当前成员有权图片。
- 新增/修改/删除图片产生 outbox，并在目标时限内反映到 Qdrant。
- 关键词和语义通道任一故障时仍有明确降级；DashScope 故障不丢失确定性结果。
- 取消后不再出现答案/成功事件；失败或取消任务能用新派发令牌重试。
- SSE 断开后用持久事件游标恢复，不重复拼接旧答案。
- 真实 golden set 权限泄露率必须为 0，再评估其他排序门槛。

## 4. 回滚与故障处理

- Agent 故障：隐藏前端入口并停止 Java 派发，原图库接口保持可用。
- DashScope 故障：清空视觉模型/模型 Key 配置，保留确定性 MySQL 检索。
- Qdrant 故障：停索引 Worker，保留 outbox 待恢复；检索降级到关键词通道。
- Redis 故障：暂停新 Agent 任务，修复 checkpoint 实例后再恢复，禁止把旧 checkpoint 当权限凭据。
- 索引错误：停止 Worker、保留 MySQL/outbox，重建新集合并切换集合名，不原地删除唯一可用集合。
- 疑似密钥泄露：立即轮换 DashScope、COS 和内部服务密钥，旧任务令牌随密钥轮换失效并审计相关任务。
