# Step 74：跨服务追踪与延迟直方图

- Python 使用真实 OpenTelemetry SDK 对任务、Java回调、意图、向量召回和视觉模型生成 span；W3C traceparent 从Java派发传入后台任务并回传Java回调。
- Java派发/回调输出同一traceId关联日志。Python使用本地JSON exporter，仅输出名称、关联ID、耗时、状态；不记录参数、URL、提示词、图像、Token或异常消息。Java关联日志不等同于Java SDK span。
- 已处理的任务失败也标记为错误；Prometheus新增固定低基数操作延迟直方图/错误计数和首段答案延迟。可计算P95，但未做真实负载验收。
- 使用真实SDK内存exporter测试父子关系、回调header、异常脱敏和标签基数约束；仅项目venv新增依赖，不启动或部署服务。
- 云端/远端collector未配置，不默认向外发送追踪数据。上线可将本地JSON收集至获批日志系统；完整Java自动埋点、OTLP平台与告警属于部署观测接入工作。
- 依据：[OpenTelemetry Python官方埋点文档](https://opentelemetry.io/docs/languages/python/instrumentation/)。
