# Step 77：P0版本化回归门禁

- 增加8条版本化contract golden：权限撤回、上传人、比例、亮度、颜色、时间排序、排除及空结果。运行真实LangGraph/检索执行器和内存checkpoint，Java/检索输入采用受控fixture。
- 命令：在 agent-service 下运行 `python -m app.evaluation.p0_gate evals/p0.contract-v1.json`；任一用例失败返回非零状态。
- 增加GitHub Actions：Python全量回归+golden、Java Agent回归、Vue生产构建；只读仓库权限，无部署、无业务凭据、无付费模型调用。
- 这不是线上端到端测试或真实标注图像评测。现有单元测试覆盖模型请求schema、取消、重试、预算、签名与权限等路径；真人标签、模型实际检索效果和性能门槛仍需部署后的验收数据。
- 前端门禁使用build-only；原项目全量vue-tsc历史问题尚未作为本次Agent P0完成依据。
