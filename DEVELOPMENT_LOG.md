# Agent 开发记录

## 2026-09-07：开发基线

- 保存现有图库前端、两个后端及 Agent 独立目录。
- 确认 MVP 范围、DashScope 模型和服务端权限校验策略。
- Agent 已实现 RRF 排名融合；6 个基础单元测试通过。
- 完整 MVP 尚未实现，也未部署任何新增服务。
- 前端此前的全量类型检查存在既有错误，不能声明全量检查通过。

## 后续记录规则

### 已完成的小步骤

- ad1274b：可重放 Python 图片索引 Worker，25 项 Python 测试通过，已同步 GitHub。
- 本次：Java 取消事件与 Python 分阶段取消检查、终态竞争保护，见 agent-service/STEP-24.md。

- c82b1f0：索引任务 Worker 令牌、租约 claim/ack 和失败退避，35 项 Java Agent 测试通过，已同步 GitHub。
- 本次：DashScope embedding、Qdrant upsert/delete 与可靠 ack 的 Python 索引 Worker，见 agent-service/STEP-23.md。

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
# 2026-09-07 - Step 25：LangGraph 持久化工作流

- 以用户 ID + 会话 ID 隔离 Redis checkpoint，保存最近 8 轮结构化检索摘要。
- 将检索编排拆分为三个可恢复节点，各节点执行前复核任务活动状态。
- 增加 Redis checkpointer 配置模板和跨轮隔离测试；本步不连接或修改本机 Redis。
# 2026-09-07 - Step 26：视觉模型安全图片入口

- 新增任务级视觉输入接口，完整复用会话归属和图片读取权限校验。
- 只为最多 8 张缩略图签发 120 秒 COS GET 地址，并限制对象域名和路径。
- 增加授权后签名、批量上限测试；本步不连接 DashScope 或修改 COS。
# 2026-09-07 - Step 27：DashScope 视觉分析适配器

- 新增 Qwen 视觉模型适配器，只消费 Java 复核权限后签发的短期 HTTPS 图片地址。
- 限制单批图片数，要求回答引用 pictureId 并区分视觉观察和实验事实。
- 模型失败自动降级到确定性检索答案；测试不访问真实 DashScope。
# 2026-09-07 - Step 28：Agent 会话列表契约

- 增加当前登录用户的最近 50 个 Agent 会话查询接口。
- 对外隐藏 userId，大整数空间 ID 使用字符串传输，为前端工作台提供稳定契约。
# 2026-09-07 - Step 29：会话任务历史契约

- 增加会话内最近 50 个任务查询，访问前校验当前用户的会话归属。
- 任务 VO 补充时间字段，使前端可在刷新后按任务回放持久化事件。
# 2026-09-07 - Step 30：前端 Agent 工作台

- 新增会话、消息、任务、历史事件 API 封装和支持凭据的 SSE 客户端。
- 新增视觉资产 Agent 页面、侧栏与路由，支持刷新回放、取消、重试和引用跳转。
- 页面仅展示执行阶段与证据，不暴露隐藏思维链或后端服务密钥。
# 2026-09-07 - Step 31：Agent 总任务截止时间

- 增加跨检索、鉴权和视觉分析的总截止时间预算，默认 120 秒。
- 超时使用独立错误码和阶段，且不会覆盖已经取消的任务终态。
# 2026-09-07 - Step 32：离线检索评测基线

- 新增 JSONL 评测 CLI，覆盖 Recall@20、Precision@10、MRR、nDCG@10 与权限泄露率。
- 缺失结果按零分计算，输入严格校验；示例数据不对应真实数据库。
# 2026-09-07 - Step 33：Agent 运行指标

- 新增 Prometheus 文本指标端点，记录低基数任务结果、总耗时和空检索次数。
- 指标标签使用固定白名单，不采集用户查询、图片 URL 或身份信息。
# 2026-09-07 - Step 34：代码验收与部署交接

- 最终回归：Java Agent 39 项、Python Agent 37 项通过，前端生产构建与目标 ESLint 通过。
- 明确只读 MVP 的完成范围与后续 P1/P2 边界，避免把未部署和未调优描述为已上线。
- 新增迁移、启动、冒烟、降级、回滚和密钥泄露处置 Runbook。

# 2026-09-08 - Step 35：图片 AI 特征与双向量索引

- 新增 `picture_ai_feature` 迁移和特征状态回写，保存 caption/OCR、内容哈希、感知哈希和质量指标。
- 索引 Worker 使用受控签名缩略图生成文本/图片命名向量，Qdrant 增加完整权限与元数据 payload index。
- Python 全量 39 项测试通过，Java Agent 39 项测试通过；未执行迁移或连接真实外部服务。
- 详细交付记录见 `agent-service/STEP-35.md`。

# 2026-09-08 - Step 36：平台图片示例检索

- 消息任务支持持久化最多 5 张平台示例图片，并在任务创建前完成 Java 权限校验。
- 使用 Qdrant `image_dense` 执行同权限范围的视觉相似召回，结果回源 Java 二次鉴权后参与加权 RRF 融合。
- 前端工作台支持图片 ID 选择，图片详情页提供自动携带图片与空间上下文的“Agent 查相似”入口。
- Python 41 项、Java Agent 41 项测试及前端生产构建通过；详细记录见 `agent-service/STEP-36.md`。
