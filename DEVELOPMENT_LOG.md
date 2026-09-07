# Agent 开发记录

## 2026-09-07：开发基线

- 保存现有图库前端、两个后端及 Agent 独立目录。
- 确认 MVP 范围、DashScope 模型和服务端权限校验策略。
- Agent 已实现 RRF 排名融合；6 个基础单元测试通过。
- 完整 MVP 尚未实现，也未部署任何新增服务。
- 前端此前的全量类型检查存在既有错误，不能声明全量检查通过。

## 后续记录规则

### 已完成的小步骤

- ce258d2：图片索引 outbox、触发器和历史图片幂等补事件，32 项 Java Agent 回归通过，已同步 GitHub。
- 本次：带短期 Worker 令牌、数据库租约、失败退避的 claim/ack 接口，见 agent-service/STEP-22.md。

- 4dcb718：Qdrant collection 与 payload index 可重复初始化，22 项 Python 测试通过，已同步 GitHub。
- 本次：图片增删改、审核和空间变化的 MySQL 索引 outbox，见 agent-service/STEP-21.md。

- fdc22b5：DashScope 文本向量、Qdrant 范围查询和授权后 RRF，19 项 Python 测试通过，已同步 GitHub。
- 本次：Qdrant collection 与 payload index 的可重复初始化命令，见 agent-service/STEP-20.md。

- f41e4c6：外部索引候选 Java 回源鉴权，32 项 Java Agent 测试通过，已同步 GitHub。
- 本次：DashScope 文本向量、Qdrant 范围过滤及授权后 RRF 融合，见 agent-service/STEP-19.md。

- bdb07e2：DashScope 结构化检索意图及故障降级，16 项 Python 测试通过，已同步 GitHub。
- 本次：Qdrant 等外部索引候选的 Java 回源逐项鉴权，见 agent-service/STEP-18.md。

- 761b00e：Python 权限安全关键词执行器，14 项 Python 测试通过，已同步 GitHub。
- 本次：DashScope 结构化检索意图与无密钥/故障降级，见 agent-service/STEP-17.md。

- 5f83b37：权限安全的 Java 图片关键词召回，31 项 Java Agent 测试通过，已同步 GitHub。
- 本次：Python 默认关键词检索执行器和可恢复的工具/引用/答案事件，见 agent-service/STEP-16.md。

- 3080ffa：Python 受保护任务接收与 Java 状态/事件回调，12 项 Python 测试通过，已同步 GitHub。
- 本次：权限安全的 Java 图片关键词召回内部工具，见 agent-service/STEP-15.md。

- 2c47df1：事务提交后的 Java→Python 异步任务分发，29 项 Agent 测试通过，已同步 GitHub。
- 本次：Python 受保护任务接收、重复分发防护及 Java 状态/事件回调，见 agent-service/STEP-14.md。

- 9e5707f：令牌保护的 Java 内部任务网关，25 项 Agent 测试通过，已同步 GitHub。
- 本次：事务提交后的 Java→Python 异步任务分发和失败落库，见 agent-service/STEP-13.md。

- cc719f8：Python 服务基础及兼容令牌验签，9 项 Python 测试通过，已同步 GitHub。
- 本次：令牌保护的 Java 内部任务上下文、事件与状态接口，见 agent-service/STEP-12.md。

- 2a56c38：Java 短期服务上下文，22 项 Agent 测试通过，已同步 GitHub。
- 本次：Python FastAPI 配置与兼容的短期令牌验签，见 agent-service/STEP-11.md。

- ba78e25：可恢复 SSE 任务事件流，20 项测试通过，已同步 GitHub。
- 本次：绑定任务/会话/用户/空间的 5 分钟 HMAC 服务上下文，见 agent-service/STEP-10.md。

- 49c0109：持久任务事件和断线增量补拉，18 项测试通过，已同步 GitHub。
- 本次：SSE 实时事件、Last-Event-ID 恢复和连接前权限校验，见 agent-service/STEP-09.md。

- 2fe0b60：任务取消和失败/取消重试，15 项 Agent 测试通过，已同步 GitHub。
- 本次：持久任务事件与基于 afterEventId 的权限安全增量补拉，见 agent-service/STEP-08.md。

- 9295d6a：任务持久化及归属安全的任务查询，12 项回归测试通过，已同步 GitHub。
- 本次：任务取消、条件状态更新和失败/取消重试，见 agent-service/STEP-07.md。

- 334e642：用户消息持久化，9 项 Agent 回归测试通过，已同步 GitHub。
- 本次：消息提交与 PENDING 任务在同一事务创建，并提供归属安全的任务查询，见 agent-service/STEP-06.md。

- f2a487e：会话空间绑定和跨范围拒绝，6 项回归测试通过，已同步 GitHub。
- 本次：用户消息持久化与会话内读写接口，见 agent-service/STEP-05.md。

- 20b10e6：MySQL 会话持久化，5 项单元测试通过；未执行数据库迁移。
- 本次：会话绑定指定空间和跨范围拒绝，见 agent-service/STEP-04.md；测试与同步结果见提交正文。

- c2d7d55：指定空间权限范围，2 项测试通过，已同步 GitHub。
- 4433814：Redis 会话归属与图片元数据访问，4 项测试通过，已同步 GitHub。
- 本次：MySQL 持久会话归属及增量建表脚本，详见 agent-service/STEP-03.md；最终验证记录在提交正文。
- 前两步的记录缺口已补齐。此处列出已完成子步骤，不代表整个阶段 3 完成。

按需求文档阶段 0～7 推进，每个可验证的小步骤提交一次。
提交正文记录阶段、变更和测试；阶段达到验收标准后才创建阶段标签。
每次同步 GitHub 前检查暂存差异与敏感配置，不提交密钥或运行数据。
