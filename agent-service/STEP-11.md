# Python Agent 服务安全基础

建立 FastAPI 应用入口、环境配置、依赖分组和健康检查。
实现与 Java AgentServiceTokenService 兼容的 HMAC-SHA256 令牌验证，检查签名、任务绑定、签发时间、5 分钟固定 TTL，并将所有业务 ID 保留为字符串。

基础安全测试只依赖 Python 标准库，无需安装 FastAPI、模型或向量库依赖。
本步骤没有启动服务，也没有调用 DashScope。模型密钥、内部服务密钥均只从环境变量读取。
