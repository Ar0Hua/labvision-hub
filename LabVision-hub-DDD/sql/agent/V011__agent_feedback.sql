-- 开发阶段仅提供迁移，不自动执行。
CREATE TABLE IF NOT EXISTS agent_feedback (
 id bigint NOT NULL AUTO_INCREMENT PRIMARY KEY,
 taskId varchar(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 userId bigint NOT NULL,
 pictureId bigint NOT NULL,
 label varchar(32) NOT NULL,
 createTime datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
 updateTime datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
 UNIQUE KEY uk_feedback (taskId,userId,pictureId),
 CONSTRAINT fk_feedback_task FOREIGN KEY (taskId) REFERENCES agent_task(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
