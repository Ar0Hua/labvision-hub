# 第 20 步：Qdrant collection 可重复初始化

## 本步完成

- 新增命令 `labvision-qdrant-init`，根据环境配置创建向量 collection。
- collection 使用与 DashScope embedding 一致的可配置维度和 Cosine 距离。
- 为 `scopeKey` 与 `pictureId` 创建 keyword payload index，支撑范围过滤和候选回源。
- 初始化可重复执行；已有 collection 的维度或距离不兼容时明确终止，不自动删除或重建数据。
- Qdrant API key 仅从环境变量读取。

## 使用前提

在 `agent-service` 安装项目依赖并配置 `AGENT_INTERNAL_SECRET`、Qdrant 连接参数后，执行：

```powershell
labvision-qdrant-init
```

这是一项会创建 collection/index 的显式运维命令，本次开发未替用户执行。

## 尚未完成

- collection 目前没有图片向量；下一步实现 MySQL outbox 与可重放索引 worker。
