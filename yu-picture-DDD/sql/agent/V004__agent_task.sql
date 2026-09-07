-- 在 V003 后执行；本次开发不自动修改数据库。
CREATE TABLE IF NOT EXISTS agent_task (
    id varchar(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL PRIMARY KEY,
    conversationId varchar(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    inputMessageId varchar(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    userId bigint NOT NULL,
    status varchar(16) NOT NULL DEFAULT 'PENDING',
    stage varchar(32) NOT NULL DEFAULT 'QUEUED',
    errorCode varchar(64) NULL,
    errorMessage varchar(512) NULL,
    createTime datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updateTime datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_agent_task_conversation_time (conversationId, createTime),
    INDEX idx_agent_task_user_status (userId, status),
    CONSTRAINT fk_agent_task_conversation FOREIGN KEY (conversationId)
        REFERENCES agent_conversation(id) ON DELETE CASCADE,
    CONSTRAINT fk_agent_task_input_message FOREIGN KEY (inputMessageId)
        REFERENCES agent_message(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
