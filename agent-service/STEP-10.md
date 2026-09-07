# Java 与 Agent 服务短期签名上下文

新增 HMAC-SHA256 短期令牌，绑定 taskId、conversationId、userId 和可选 spaceId，有效期 5 分钟。
所有 bigint 标识在令牌中使用字符串。验签采用常量时间比较，同时检查任务绑定、签发时间、过期时间和固定 TTL。

Java 运行前必须通过 AGENT_INTERNAL_SECRET 或 agent.internal.secret 配置至少 32 字符的随机密钥。
密钥不得写入仓库；Python Agent 服务必须使用同一值。当前仅实现签发/验签核心，下一步接入内部工具接口和任务派发。
