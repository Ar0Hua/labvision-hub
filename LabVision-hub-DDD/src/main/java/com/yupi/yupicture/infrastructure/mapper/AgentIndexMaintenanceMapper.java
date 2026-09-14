package com.yupi.yupicture.infrastructure.mapper;

import org.apache.ibatis.annotations.*;
import java.util.*;

/** Cursor scan uses numeric IDs, never OFFSET; includes soft-deleted rows for index cleanup. */
public interface AgentIndexMaintenanceMapper {
    @Select("SELECT CAST(p.id AS CHAR) AS pictureId, p.isDelete, p.spaceId, p.reviewStatus, "
        + "UNIX_TIMESTAMP(COALESCE(p.updateTime,p.editTime,p.createTime)) AS sourceUpdatedAtEpoch, "
        + "f.indexStatus, f.embeddingVersion FROM picture p LEFT JOIN picture_ai_feature f ON f.pictureId=p.id "
        + "WHERE p.id>#{after} ORDER BY p.id LIMIT #{limit}")
    List<Map<String,Object>> scan(@Param("after") long after, @Param("limit") int limit);

    @Insert("INSERT IGNORE INTO agent_picture_index_outbox(pictureId,operation,dedupeKey) "
        + "VALUES(#{pictureId},'UPSERT',#{dedupeKey})")
    int enqueue(@Param("pictureId") long pictureId, @Param("dedupeKey") String dedupeKey);
}
