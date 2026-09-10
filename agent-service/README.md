# LabVision Agent

独立的实验室视觉资产检索与分析服务，接入现有 DDD Java 后端和 Vue 前端。

## 实施状态

已补齐本轮核对的只读P0功能代码（最多20张图片MVP），包括权限检索、临时图、真实模型流式适配、部分成果保留、预算、追踪与回归门禁。代码回归通过不代表完整P0验收通过：尚未部署服务、执行迁移、回填历史图片或完成真实模型/中间件联调和效果压测。当前能力与边界以 [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md) 为准，部署步骤见 [DEPLOYMENT-RUNBOOK.md](DEPLOYMENT-RUNBOOK.md)。

## 已确认决策

- Python 3.11+、FastAPI、LangGraph，模型使用千问/DashScope。
- Java 11 / Spring Boot 2.7.6 保持为登录、图片和空间权限事实源。
- Qdrant 为独立向量数据库；开发阶段不要求部署，后续接入真实索引。
- 用户授权：当前用户可查看的图片可以发送给 DashScope。服务端必须先验证会话归属和当前图片权限；不能以客户端传入的用户 ID 或会话 ID 作为授权证据。
- 查看权限只允许读取和分析；修改仍须编辑权限及审批。MVP 不开放写工具。
- 前端通过 Java 同域 API 访问 Agent，密钥不下发浏览器。

## 开发顺序与验收

- [x] 固化开发范围和权限边界，建立独立目录。
- [x] 实现不依赖外部服务的多路排名融合核心及单元测试。
- [x] Java 权限范围解析、短期用户上下文和内部只读工具。
- [x] MySQL 会话、任务、审计事件和 outbox 增量迁移脚本。
- [x] 索引 worker、中文文本 embedding 适配、Qdrant 候选回源权限复核。
- [x] DashScope 结构化意图、视觉分析和引用约束。
- [x] LangGraph 有界多轮状态、Redis 持久 checkpoint、取消与失败终态保护。
- [x] 前端工作台、SSE 事件恢复、引用跳转和分析结果。
- [x] 权限变化回源复核、索引失败重试、模型失败降级和检索评测基线。

## 本地测试

在本目录执行 `python -m unittest discover -s tests -v`。基础算法测试无需模型密钥、网络或中间件。

配置模板见 `.env.example`。环境文件不提交版本库。模型与向量适配器接入前不将占位输出视为真实检索结果。
