ALTER TABLE agent_task ADD COLUMN temporaryImageId VARCHAR(36) NULL COMMENT 'TTL-bound input, never a permanent picture ID';
