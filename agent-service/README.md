# LabVision Agent

实验室视觉资产检索与分析服务，连接 DDD Java 后端、Vue 前端、Redis、Qdrant 和千问/DashScope。

## 代码入口

- `app/main.py`：FastAPI 服务入口。
- `app/graph/`、`app/runtime/`：对话状态、任务执行与恢复。
- `app/retrieval/`：关键词、文本与图像向量检索、筛选和排序。
- `app/analysis/`：单图、图片组及空间统计分析。
- `app/indexing/`：图片特征、向量集合与索引 Worker。
- `app/security/`、`app/observability/`：内部签名校验、运行指标与追踪。
- `tests/`、`evals/`：自动化回归与检索评测。

## 配置与运行

使用 Python 3.11 或更高版本，依赖及命令入口见 `pyproject.toml`。配置模板见 [.env.example](.env.example)，部署与服务启动顺序见 [DEPLOYMENT-RUNBOOK.md](DEPLOYMENT-RUNBOOK.md)。真实密钥仅保存在本地环境配置中。

Java 后端负责登录、会话归属和图片访问权限；向量候选需回源复核权限。当前 Agent 提供只读检索与分析，单次图片组最多 20 张。前端通过 Java API 访问 Agent。

## 测试

在本目录且已安装开发依赖的环境中执行：

```sh
python -m pytest -q
python -m app.evaluation.p0_gate evals/p0.contract-v1.json
```

自动化契约使用受控测试数据；真实模型效果、权限场景与性能需在目标环境另行验收。
