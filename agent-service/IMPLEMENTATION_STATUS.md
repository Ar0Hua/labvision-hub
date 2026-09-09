# LabVision Agent 代码完成状态

更新时间：2026-09-09

## 已完成的只读检索与分析核心

- Java 作为登录、会话、空间 RBAC、图片权限和任务状态事实源。
- 会话、消息、任务、SSE 事件、取消、失败重试及事务提交后派发。
- 服务令牌与 Worker 令牌分用途签名，绑定用户、会话、空间和任务。
- 权限范围内 MySQL 关键词召回、DashScope embedding、Qdrant 召回和 RRF 融合。
- 平台图片示例的 `image_dense` 站内相似检索，示例与结果均由 Java 校验权限。
- 格式、日期、尺寸、文件大小等结构化条件在 MySQL 和 Qdrant 各召回通道一致生效。
- 多轮追问可继承、覆盖或重置结构化条件，并可排除上一轮结果或以其继续相似检索。
- DDD 后端提供绑定签名任务范围的确定性空间统计摘要内部接口。
- transactional outbox、租约领取、确认/重试和可重放索引 Worker。
- LangGraph 三阶段工作流、Redis checkpoint、有界结构化会话摘要和总任务超时。
- Java 再鉴权后的短期 COS 缩略图 URL，以及 DashScope/Qwen 视觉观察。
- Vue Agent 工作台、历史事件回放、SSE 续传、取消/重试和引用跳转。
- Prometheus 文本指标与 JSONL 离线检索评测 CLI。

## 尚未完成或留待后续

- Agent 自动修改图片元数据、审批令牌、变更回滚等写工具。
- 完整图片组对比、空间统计自然语言问答与结果反馈闭环。
- PDF 报告、大规模聚类/相似度矩阵和空间级自然语言统计编排。
- 用户临时上传图片供 Agent 分析。
- 真实环境阈值调优、灰度发布与云端服务部署。

以上能力在完成代码、测试或真实环境验收前，不应描述为已实现或已上线。

## 验证结果

- Java Agent：Step 40 全量 45 项测试通过。
- Python Agent：Step 39 全量 48 项测试通过。
- 前端：Step 36 Vite 生产构建成功。
- 未连接真实 DashScope、Qdrant、COS 或生产数据库，未执行任何迁移。

仓库原有完整 `npm run build` 的类型检查仍存在非 Agent 历史错误；`npm run build-only` 成功，但保留 `GlobalHeader.vue` 的既有类型导入警告及大包警告。
