-- 在 V001 之后执行一次；先核对列是否存在，本次开发不执行。
-- 旧会话绑定公共图库，空间会话需重新创建。
ALTER TABLE agent_conversation ADD COLUMN spaceId bigint NULL COMMENT '绑定空间，NULL为公共图库';
