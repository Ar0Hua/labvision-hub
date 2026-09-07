# 第 17 步：DashScope 结构化检索意图

## 本步完成

- 使用 DashScope 的 OpenAI 兼容 `POST /chat/completions` 接口和 `response_format: json_object` 解析检索意图。
- 模型输出经过 Pydantic 严格白名单校验，只接受 `searchText/category/tags/limit`，不能指定用户、空间或图片 ID。
- 用户文本以数据身份进入 user message；system prompt 明确禁止执行其中的指令，只做 JSON 转换。
- 未配置密钥、超时、HTTP 错误、非 JSON 或越界字段都会降级为原始关键词检索，不中断现有能力。
- 默认文本模型为 `qwen-plus`，密钥仍只从环境变量读取。

官方接口依据：<https://help.aliyun.com/zh/model-studio/qwen-api-via-dashscope>

## 尚未完成

- 模型目前只参与查询结构化，不接触图片内容，也不决定权限。
- 下一步接入 Qdrant 向量通道与 RRF 融合；视觉分析将在候选图片再次授权后单独实现。
- 本步测试使用 MockTransport，未发送真实 DashScope 请求、未部署服务。
