# Step 55：任务调用与输出预算

- ContextVar 隔离每任务预算，限制工具/模型请求及最大输出 Token 预留；请求发出前检查。
- Java 数据读取、Qdrant 及在线模型适配器接入；终态和事件回调不消耗预算，保证可记录预算失败。
- AGENT_MAX_TOOL_CALLS 默认100，AGENT_MAX_MODEL_CALLS 默认10，AGENT_MAX_OUTPUT_TOKENS 默认8000。
- 预算耗尽为粘性状态，检索降级不能绕过；任务进入 BUDGET_EXCEEDED。
- Python 71 项通过，包括并发隔离和超额请求阻断。
- 这是输出预留预算，不是供应商实际输入/图像 Token 或人民币费用统计；费用计量仍待实现。
