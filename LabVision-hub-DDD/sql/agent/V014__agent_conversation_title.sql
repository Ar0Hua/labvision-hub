-- 对话名称；删除复用现有 status 字段，历史消息保留用于审计。
ALTER TABLE agent_conversation ADD COLUMN title varchar(60) NULL AFTER status;
