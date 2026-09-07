-- 在 V007 后执行；本次开发不自动修改数据库。
ALTER TABLE agent_picture_index_outbox
    ADD COLUMN leaseToken varchar(36) CHARACTER SET ascii COLLATE ascii_bin NULL AFTER lockedAt;
CREATE INDEX idx_agent_picture_outbox_lease ON agent_picture_index_outbox (id, status, leaseToken);
