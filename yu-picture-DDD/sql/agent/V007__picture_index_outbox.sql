-- 在 V001-V006 后手动执行；本次开发不自动修改数据库。
-- 触发器确保任何写入路径（包括批量更新和逻辑删除）都产生索引事件。
CREATE TABLE IF NOT EXISTS agent_picture_index_outbox (
    id bigint NOT NULL AUTO_INCREMENT PRIMARY KEY,
    pictureId bigint NOT NULL,
    operation varchar(16) NOT NULL,
    status varchar(16) NOT NULL DEFAULT 'PENDING',
    attemptCount int NOT NULL DEFAULT 0,
    availableAt datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
    lockedAt datetime NULL,
    lastError varchar(512) NULL,
    dedupeKey varchar(128) NULL,
    createTime datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updateTime datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE INDEX uk_agent_picture_outbox_dedupe (dedupeKey),
    INDEX idx_agent_picture_outbox_claim (status, availableAt, id),
    INDEX idx_agent_picture_outbox_picture (pictureId, id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TRIGGER IF EXISTS trg_agent_picture_index_insert;
DROP TRIGGER IF EXISTS trg_agent_picture_index_update;
DROP TRIGGER IF EXISTS trg_agent_picture_index_delete;

DELIMITER //
CREATE TRIGGER trg_agent_picture_index_insert
AFTER INSERT ON picture FOR EACH ROW
BEGIN
    INSERT INTO agent_picture_index_outbox(pictureId, operation)
    VALUES (NEW.id, IF(NEW.isDelete = 1 OR (NEW.spaceId IS NULL AND NOT (NEW.reviewStatus <=> 1)),
            'DELETE', 'UPSERT'));
END//

CREATE TRIGGER trg_agent_picture_index_update
AFTER UPDATE ON picture FOR EACH ROW
BEGIN
    IF NOT (NEW.url <=> OLD.url)
       OR NOT (NEW.thumbnailUrl <=> OLD.thumbnailUrl)
       OR NOT (NEW.name <=> OLD.name)
       OR NOT (NEW.introduction <=> OLD.introduction)
       OR NOT (NEW.category <=> OLD.category)
       OR NOT (NEW.tags <=> OLD.tags)
       OR NOT (NEW.spaceId <=> OLD.spaceId)
       OR NOT (NEW.reviewStatus <=> OLD.reviewStatus)
       OR NOT (NEW.isDelete <=> OLD.isDelete) THEN
        INSERT INTO agent_picture_index_outbox(pictureId, operation)
        VALUES (NEW.id, IF(NEW.isDelete = 1 OR (NEW.spaceId IS NULL AND NOT (NEW.reviewStatus <=> 1)),
                'DELETE', 'UPSERT'));
    END IF;
END//

CREATE TRIGGER trg_agent_picture_index_delete
AFTER DELETE ON picture FOR EACH ROW
BEGIN
    INSERT INTO agent_picture_index_outbox(pictureId, operation)
    VALUES (OLD.id, 'DELETE');
END//
DELIMITER ;

-- 首次执行时为历史有效图片补事件；dedupeKey 使该段可安全重放。
INSERT IGNORE INTO agent_picture_index_outbox(pictureId, operation, dedupeKey)
SELECT id, 'UPSERT', CONCAT('bootstrap:', id)
FROM picture
WHERE isDelete = 0 AND (spaceId IS NOT NULL OR reviewStatus = 1);
