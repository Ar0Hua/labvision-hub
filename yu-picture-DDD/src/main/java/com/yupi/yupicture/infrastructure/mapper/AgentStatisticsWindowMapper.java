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
}
