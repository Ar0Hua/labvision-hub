-- 在 V004 后执行；本次开发不自动修改数据库。
ALTER TABLE agent_task ADD COLUMN retryCount int NOT NULL DEFAULT 0;
