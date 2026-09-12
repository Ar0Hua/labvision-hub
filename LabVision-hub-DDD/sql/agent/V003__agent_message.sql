-- 在 V001、V002 后执行；本次开发不自动修改数据库。
CREATE TABLE IF NOT EXISTS agent_message (
 id varchar(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL PRIMARY KEY,
 conversationId varchar(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 userId bigint NOT NULL, role varchar(16) NOT NULL, content text NOT NULL,
 createTime datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
 INDEX idx_agent_message_conversation_time (conversationId,createTime,id),
 CONSTRAINT fk_agent_message_conversation FOREIGN KEY (conversationId) REFERENCES agent_conversation(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
