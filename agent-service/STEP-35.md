# Step 35：图片 AI 特征与双向量索引

## 对应文档

- 阶段 1：图片 AI 特征与索引管道
- FR-01：文本语义召回、视觉向量召回及可解释质量特征

## 本步完成

- 新增 `picture_ai_feature` 迁移、DDD 实体和 Mapper，保存 caption、OCR、内容哈希、pHash/dHash、亮度、模糊度、质量标记、模型版本和索引状态。
- Java Worker 网关返回当前图片版本、权限过滤字段和 300 秒 COS 签名缩略图；成功/失败/删除均同步特征状态。
- Python Worker 校验图片响应类型与大小，执行图片解码校验，计算 SHA-256、pHash、dHash、亮度与模糊度。
- 使用千问视觉模型生成受控 caption/OCR，使用 DashScope 文本和多模态 embedding 生成 `text_dense`、`image_dense`。
- Qdrant collection 改为命名向量，并为权限、审核、时间、分类、哈希等高频过滤字段创建 payload index。
- 修复 Python 包发现范围，使项目可在 `.venv` 中执行可编辑安装。

## 安全与一致性

- Worker 只处理 Java 网关签发的短期 COS URL，不接收任意客户端 URL。
- Qdrant payload 同时写入 `scopeKey`、审核状态和删除状态，查询结果仍必须回源 Java 二次鉴权。
- point ID 固定为 pictureId，重复消费保持幂等；删除事件同时移除 Qdrant point 与 MySQL 特征记录。
- 向量模型或 schema 变化必须使用新 collection/蓝绿重建，旧的单向量 collection 会被兼容性校验拒绝。

## 验证

- Python：`39 passed`。
- Java Agent：`39 tests`，全部通过。
- 完整 Maven 套件仍包含两个项目原有的错误包名 SpringBoot 测试，和本步代码无关。
- 本步没有执行数据库迁移，没有连接真实 DashScope、COS 或 Qdrant。
