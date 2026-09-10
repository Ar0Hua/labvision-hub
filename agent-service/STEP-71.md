# Step 71：供应商流式视觉输出

- 实际任务的视觉分析和临时图分析使用 DashScope 兼容 SSE，启用 stream 与 include_usage；消费 delta.content，不读取隐藏 reasoning_content。
- 完整段落校验允许 pictureId 后即时发布；跨事件引用先拼接再校验。拒绝未知ID、URL、超长文本及缺少DONE的截断流。
- 已完成段落和批次即时持久化，后续模型/鉴权/预算失败保留前缀；跨批摘要仍为有界一次性归纳。
- 流接收时每秒检查任务状态，段落发布前仍由任务发布链路复核。断开静默流的最坏等待受模型HTTP超时约束；未声称首token P95达标。
- 保留非流式分析适配器供离线测试；实际运行选择流式路径。自动化覆盖分段、隐藏推理、未知引用和断流。
- 协议依据：[阿里云流式输出文档](https://www.alibabacloud.com/help/zh/model-studio/stream)。未调用真实付费模型。
