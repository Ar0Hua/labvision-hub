package com.yupi.yupicture.infrastructure.mapper;
import org.apache.ibatis.annotations.*;
import java.util.*;

public interface AgentStatisticsWindowMapper {
    String FILTER = " WHERE p.isDelete=0 AND ((#{spaceId} IS NULL AND p.spaceId IS NULL AND p.reviewStatus=1)"
            + " OR (#{spaceId} IS NOT NULL AND p.spaceId=#{spaceId}))"
            + " AND (#{start} IS NULL OR p.createTime >= #{start})"
            + " AND (#{end} IS NULL OR p.createTime < #{end})"
            + " AND (#{uploaderId} IS NULL OR p.userId=#{uploaderId})";
    @Select("SELECT COUNT(*) AS count,COALESCE(SUM(p.picSize),0) AS totalSize FROM picture p" + FILTER + "")
    Map<String,Object> totals(@Param("spaceId") Long spaceId,@Param("start") java.util.Date start,@Param("end") java.util.Date end,@Param("uploaderId") Long uploaderId);
    @Select("SELECT p.category AS category,COUNT(*) AS count,COALESCE(SUM(p.picSize),0) AS totalSize FROM picture p" + FILTER + " GROUP BY p.category ORDER BY count DESC,p.category LIMIT 20")
    List<Map<String,Object>> categories(@Param("spaceId") Long spaceId,@Param("start") java.util.Date start,@Param("end") java.util.Date end,@Param("uploaderId") Long uploaderId);
    @Select("SELECT CAST(p.userId AS CHAR) AS uploaderId,COUNT(*) AS count FROM picture p" + FILTER + " GROUP BY p.userId ORDER BY count DESC,p.userId LIMIT 20")
    List<Map<String,Object>> uploaders(@Param("spaceId") Long spaceId,@Param("start") java.util.Date start,@Param("end") java.util.Date end,@Param("uploaderId") Long uploaderId);
    @Select("SELECT DATE_FORMAT(p.createTime,'%Y-%m') AS period,COUNT(*) AS count FROM picture p" + FILTER + " GROUP BY DATE_FORMAT(p.createTime,'%Y-%m') ORDER BY period DESC LIMIT 24")
    List<Map<String,Object>> trend(@Param("spaceId") Long spaceId,@Param("start") java.util.Date start,@Param("end") java.util.Date end,@Param("uploaderId") Long uploaderId);

    @Select("SELECT COUNT(*) AS totalCount,"
            + " COALESCE(SUM(p.tags IS NULL OR TRIM(p.tags)='' OR TRIM(p.tags)='[]'),0) AS untaggedCount,"
            + " COALESCE(SUM(COALESCE(p.editTime,p.updateTime,p.createTime) < #{staleBefore}),0) AS staleCount,"
            + " COALESCE(SUM(p.picWidth IS NULL OR p.picHeight IS NULL OR p.picWidth<=0 OR p.picHeight<=0),0) AS unknownResolutionCount,"
            + " COALESCE(SUM(p.picWidth>0 AND p.picHeight>0 AND p.picWidth*p.picHeight<1000000),0) AS underOneMegapixelCount,"
            + " COALESCE(SUM(p.picWidth>0 AND p.picHeight>0 AND p.picWidth*p.picHeight>=1000000 AND p.picWidth*p.picHeight<4000000),0) AS oneToFourMegapixelCount,"
            + " COALESCE(SUM(p.picWidth>0 AND p.picHeight>0 AND p.picWidth*p.picHeight>=4000000),0) AS overFourMegapixelCount,"
            + " COUNT(f.pictureId) AS indexedCount,"
            + " COALESCE(SUM(f.brightnessScore<50 OR f.brightnessScore>210 OR f.blurScore<45),0) AS qualityIssueCount,"
            + " COUNT(f.contentHash)-COUNT(DISTINCT f.contentHash) AS duplicateExcessCount"
            + " FROM picture p LEFT JOIN picture_ai_feature f ON f.pictureId=p.id AND f.indexStatus='READY'"
            + " AND UNIX_TIMESTAMP(f.sourceUpdatedAt)=FLOOR(UNIX_TIMESTAMP(COALESCE(p.updateTime,p.editTime,p.createTime)))"
            + FILTER)
    Map<String,Object> governance(@Param("spaceId") Long spaceId,@Param("start") Date start,@Param("end") Date end,
                                  @Param("uploaderId") Long uploaderId,@Param("staleBefore") Date staleBefore);

    @Select("SELECT CASE WHEN p.picSize IS NULL OR p.picSize<0 THEN 'unknown'"
            + " WHEN p.picSize<1048576 THEN '<1MB' WHEN p.picSize<10485760 THEN '1-10MB' ELSE '>=10MB' END AS sizeRange,"
            + " COUNT(*) AS count FROM picture p" + FILTER + " GROUP BY sizeRange ORDER BY sizeRange")
    List<Map<String,Object>> sizes(@Param("spaceId") Long spaceId,@Param("start") Date start,@Param("end") Date end,@Param("uploaderId") Long uploaderId);

    // MySQL 8 JSON_TABLE; malformed or non-array legacy tags are treated as unknown, not executed.
    @Select("SELECT jt.tag,COUNT(DISTINCT p.id) AS count FROM picture p JOIN JSON_TABLE("
            + " CASE WHEN JSON_VALID(p.tags) THEN CASE WHEN JSON_TYPE(p.tags)='ARRAY' THEN p.tags ELSE '[]' END ELSE '[]' END,"
            + " '$[*]' COLUMNS(tag VARCHAR(255) PATH '$' NULL ON ERROR)) jt ON TRUE"
            + FILTER + " AND jt.tag IS NOT NULL AND TRIM(jt.tag)<>'' GROUP BY jt.tag ORDER BY count DESC,jt.tag LIMIT 20")
    List<Map<String,Object>> tags(@Param("spaceId") Long spaceId,@Param("start") Date start,@Param("end") Date end,@Param("uploaderId") Long uploaderId);
}
