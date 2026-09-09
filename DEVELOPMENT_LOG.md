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

# 2026-09-08 - Step 37：混合结构化过滤

- `SearchIntent` 增加格式、日期、尺寸、文件大小和排序的严格类型约束及模型故障降级。
- Java 在已签名会话空间内执行参数化 SQL 过滤，文本/图像向量召回同步使用相同 Qdrant payload filter。
- Python→Java 契约采用字段白名单，拒绝 raw SQL、未知格式、非法日期和越界数值。
- Python 44 项、Java Agent 43 项测试通过；详细记录见 `agent-service/STEP-37.md`。

# 2026-09-09 - Step 38：多轮结构化检索状态

- LangGraph checkpoint 新增严格验证的 `SearchIntent` 状态，在同一用户与会话内继承结构化过滤条件。
- 千问根据本轮问题与上轮意图输出完整合并状态；明确重置时清空，模型故障时执行确定性继承/重置。
- 每轮空间范围仍取自新的 Java 签名任务上下文，不把旧 checkpoint 当作授权凭据。
- Python 46 项测试通过；详细记录见 `agent-service/STEP-38.md`。

# 2026-09-09 - Step 39：结果级多轮检索操作

- 千问可根据上一轮有序结果将“第 N 张”解析为受约束图片 ID，支持结果排除和继续相似检索。
- 示例图片在 Qdrant 查询前由 Java 重新校验当前权限；排除项同时进入向量过滤和最终融合过滤。
- checkpoint 仅保存严格校验后的类型化意图与图片 ID，不保存令牌、临时 URL 或图片内容。
- Python 48 项测试通过；详细记录见 `agent-service/STEP-39.md`。

# 2026-09-09 - Step 40：权限确定的空间统计内部工具

- DDD 后端复用现有空间分析服务，提供任务服务令牌保护的空间统计摘要接口。
- 用户与空间只取自重新校验后的签名任务上下文，不允许 Agent 自行扩大统计范围。
- 返回容量、数量、分类、标签、大小和月度上传趋势，并携带范围与 UTC 采集时间。
- Java Agent 45 项测试通过；详细记录见 `agent-service/STEP-40.md`。

# 2026-09-09 - Step 41：空间统计意图路由与证据回答

- Python Agent 将容量、数量、分布和上传趋势问题路由到 Java 确定性空间统计工具。
- 统计响应经过严格 Pydantic 校验，回答保留空间范围、UTC 采集时间和数据库来源说明。
- 统计任务不执行图片召回或视觉模型分析，并避免与文件大小条件检索发生路由冲突。
- Python Agent 50 项测试通过；详细记录见 `agent-service/STEP-41.md`。

# 2026-09-09 - Step 42：权限图片组的确定性元数据对比

- 对至少两张已选平台图片重新执行 Java 权限校验后，生成确定性元数据对比和真实引用。
- 输出格式、分类、方向、尺寸、大小、共同标签与代表项依据，明确隔离事实和未证实推断。
- 图片组比较使用独立工具事件，不执行关键词检索；相似度、聚类和异常检测留待向量证据步骤。
- Python Agent 52 项测试通过；详细记录见 `agent-service/STEP-42.md`。

# 2026-09-09 - Step 43：图片组受控视觉差异分析

- 图片组元数据对比后可使用 Java 重新鉴权并签发的短期缩略图执行千问视觉观察。
- 运行器按视觉配置和硬上限 8 控制输入，并在回答中披露实际覆盖张数/图片组总数。
- 模型不可用或调用失败时保留确定性分析；元数据事实与视觉观察继续分段展示。
- Python Agent 53 项测试通过；详细记录见 `agent-service/STEP-43.md`。

# 2026-09-09 - Step 44：权限图片组的 Qdrant 相似度矩阵底座

- 对 2～20 个已由 Java 鉴权的图片 ID 查询 `image_dense`，生成保持原顺序的对称余弦相似度矩阵。
- 每次查询固定当前空间、未删除条件和选中 ID 白名单，公共图库额外要求审核通过，组外结果一律丢弃。
- 双向分数取平均，对角线为 1，缺失证据保留为空；非法 ID、范围或向量分数直接拒绝。
- Python Agent 56 项测试通过；详细记录见 `agent-service/STEP-44.md`。

# 2026-09-09 - Step 45：图片组相似度回答与向量代表项

- 将权限约束的 Qdrant 相似度矩阵接入图片组最终回答，输出完整 Markdown 矩阵与真实图片引用。
- 基于已知余弦分数确定最高相似图片对和向量中心代表项，并披露图片对及代表项关联覆盖率。
- 新增独立工具事件；Qdrant 不可用时保留元数据和视觉结果，取消/超时仍按任务生命周期传播。
- Python Agent 58 项测试通过；详细记录见 `agent-service/STEP-45.md`。

# 2026-09-09 - Step 46：图片组分组与离群候选

- 接入完全链接相似分组，输出组内最低分数及图片 ID；完整向量证据下输出离群候选。
- 阈值和证据覆盖在回答中披露，缺失向量不作为离群依据，不宣称实验异常。
- Python 全量 62 项测试通过；详见 agent-service/STEP-46.md。

# Step 47：直接分析选中单图

- 完成独立单图分析路由，Python 63 项测试通过。详见 agent-service/STEP-47.md。

# Step 48：20 张图片输入与分批视觉分析

- 贯通输入上限，新增分批失败覆盖率验证；Python 64 项与 Java 边界测试通过。详见 agent-service/STEP-48.md。

# Step 49：矩阵与报告

- 增加安全表格展示、下载前鉴权和 Markdown/JSON 导出。详见 agent-service/STEP-49.md。

# Step 50：质量与查重证据

- 接通鉴权后当前版本特征查询与质量/哈希证据回答，测试通过。详见 agent-service/STEP-50.md。

# Step 51：反馈持久化

- 提供反馈迁移、接口、权限测试和前端入口，详见 agent-service/STEP-51.md。

# Step 52：检索结果鉴权与折叠

- 最终鉴权、相同索引图像折叠及匹配解释，Python 67 项通过。详见 agent-service/STEP-52.md。

# Step 53：空间治理指标

- 增加有分母和覆盖率的质量、冗余、标签、分辨率及未维护统计。详见 agent-service/STEP-53.md。

# Step 54：任务恢复

- 轮次签名、回调锁、有限自动恢复与 checkpoint 续跑，详见 agent-service/STEP-54.md。
