package com.yupi.yupicture.infrastructure.mapper;
import org.apache.ibatis.annotations.*;
import java.util.Map;

public interface AgentGovernanceMapper {
    String SCOPE = " p.isDelete=0 AND ((#{spaceId} IS NULL AND p.spaceId IS NULL AND p.reviewStatus=1)"
            + " OR (#{spaceId} IS NOT NULL AND p.spaceId=#{spaceId})) ";
    @Select("SELECT COUNT(*) AS totalCount,"
            + " COALESCE(SUM(p.tags IS NULL OR TRIM(p.tags)='' OR TRIM(p.tags)='[]'),0) AS untaggedCount,"
            + " COALESCE(SUM(COALESCE(p.editTime,p.updateTime,p.createTime) < #{staleBefore}),0) AS staleCount,"
            + " COALESCE(SUM(p.picWidth IS NULL OR p.picHeight IS NULL),0) AS unknownResolutionCount,"
            + " COALESCE(SUM(p.picWidth*p.picHeight < 1000000),0) AS underOneMegapixelCount,"
            + " COALESCE(SUM(p.picWidth*p.picHeight >= 1000000 AND p.picWidth*p.picHeight < 4000000),0) AS oneToFourMegapixelCount,"
            + " COALESCE(SUM(p.picWidth*p.picHeight >= 4000000),0) AS overFourMegapixelCount"
            + " FROM picture p WHERE " + SCOPE)
    Map<String,Object> metadata(@Param("spaceId") Long spaceId, @Param("staleBefore") java.util.Date staleBefore);
    @Select("SELECT COUNT(*) AS indexedCount,"
            + " COALESCE(SUM(f.brightnessScore < 50 OR f.brightnessScore > 210 OR f.blurScore < 45),0) AS qualityIssueCount,"
            + " COUNT(f.contentHash)-COUNT(DISTINCT f.contentHash) AS duplicateExcessCount"
            + " FROM picture p JOIN picture_ai_feature f ON f.pictureId=p.id"
            + " AND f.indexStatus='READY' AND UNIX_TIMESTAMP(f.sourceUpdatedAt)=FLOOR(UNIX_TIMESTAMP(COALESCE(p.updateTime,p.editTime,p.createTime)))"
            + " WHERE " + SCOPE)
    Map<String,Object> features(@Param("spaceId") Long spaceId);
}
