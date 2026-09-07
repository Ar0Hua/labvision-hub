# LabVision Agent 代码完成状态

更新时间：2026-09-07

## 已完成的只读 MVP

- Java 作为登录、会话、空间 RBAC、图片权限和任务状态事实源。
- 会话、消息、任务、SSE 事件、取消、失败重试及事务提交后派发。
- 服务令牌与 Worker 令牌分用途签名，绑定用户、会话、空间和任务。
- 权限范围内 MySQL 关键词召回、DashScope embedding、Qdrant 召回和 RRF 融合。
- transactional outbox、租约领取、确认/重试和可重放索引 Worker。
- LangGraph 三阶段工作流、Redis checkpoint、有界结构化会话摘要和总任务超时。
- Java 再鉴权后的短期 COS 缩略图 URL，以及 DashScope/Qwen 视觉观察。
- Vue Agent 工作台、历史事件回放、SSE 续传、取消/重试和引用跳转。
- Prometheus 文本指标与 JSONL 离线检索评测 CLI。

## 有意不在当前只读 MVP 内

- Agent 自动修改图片元数据、审批令牌、变更回滚等写工具。
- PDF 报告、大规模聚类/相似度矩阵和空间级自然语言统计编排。
- 用户临时上传图片供 Agent 分析。
- 真实环境阈值调优、灰度发布与云端服务部署。

这些属于需求文档中的后续分析/治理能力，不能在没有产品审批流程、真实标注集和部署环境的情况下宣称完成。

## 验证结果

- Java Agent：39 项测试通过。
- Python Agent：37 项测试通过。
- 前端：Vite 生产构建成功；本次修改文件 ESLint 通过。
- 未连接真实 DashScope、Qdrant、COS 或生产数据库，未执行任何迁移。

仓库原有完整 `npm run build` 的类型检查仍存在非 Agent 历史错误；`npm run build-only` 成功，但保留 `GlobalHeader.vue` 的既有类型导入警告及大包警告。
