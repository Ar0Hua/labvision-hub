# Step 54：轮次隔离、遗留任务恢复及 checkpoint 续跑

- Java 令牌加入 attempt，回调需匹配当前 retryCount；事件和状态回调加事务行锁。
- 条件更新抢占超过 10 分钟未更新的 PENDING/RUNNING 任务，最多三次自动恢复，提交后派发。
- agent.recovery.enabled=true 开启每分钟扫描；默认不启用，当前不部署服务。
- Python 同任务未完成 checkpoint 使用 invoke(None) 续跑未完成节点；图片组/统计分支重新执行只读步骤。
- Python 69 项、Java Agent 回归及新增恢复测试通过；跨进程故障演练仍需真实环境。
