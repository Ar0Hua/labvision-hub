-- 在目标数据库手动执行；先检查已有同名表的结构。本脚本不自动执行。
CREATE TABLE IF NOT EXISTS agent_conversation (
 id varchar(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL PRIMARY KEY,
 userId bigint NOT NULL,
 status varchar(16) NOT NULL DEFAULT 'ACTIVE',
 createTime datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
 updateTime datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
 INDEX idx_agent_conversation_user_time (userId, createTime)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
