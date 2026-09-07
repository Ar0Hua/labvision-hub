-- 在 V004 后执行；本次开发不自动修改数据库。
CREATE TABLE IF NOT EXISTS agent_task_event (
    id bigint NOT NULL AUTO_INCREMENT PRIMARY KEY,
    taskId varchar(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    eventType varchar(32) NOT NULL,
    payloadJson text NOT NULL,
    createTime datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_agent_task_event_task_id (taskId, id),
    CONSTRAINT fk_agent_task_event_task FOREIGN KEY (taskId)
        REFERENCES agent_task(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
