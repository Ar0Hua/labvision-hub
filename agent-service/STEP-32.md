# Step 32 - 离线检索评测基线

- 新增严格 JSONL golden set 与预测结果格式，拒绝未知字段、重复 ID 和非数字 ID。
- 计算 Recall@20、Precision@10、MRR、nDCG@10 和权限泄露率。
- 缺失预测按零分计入而不是静默忽略，权限泄露单独报告数量和比例。
- 评测程序只读取显式输入文件，不直接连接生产 MySQL、Qdrant 或模型服务。

运行：`labvision-evaluate-retrieval evals/golden.jsonl evals/predictions.jsonl`。
