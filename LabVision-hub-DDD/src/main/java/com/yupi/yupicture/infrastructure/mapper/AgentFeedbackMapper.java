package com.yupi.yupicture.infrastructure.mapper;
import org.apache.ibatis.annotations.*;
import java.util.List;
import java.util.Map;

public interface AgentFeedbackMapper {
    @Insert("INSERT INTO agent_feedback(taskId,userId,pictureId,label) VALUES(#{taskId},#{userId},#{pictureId},#{label}) "
            + "ON DUPLICATE KEY UPDATE label=VALUES(label), updateTime=CURRENT_TIMESTAMP")
    int save(@Param("taskId") String taskId, @Param("userId") Long userId,
             @Param("pictureId") Long pictureId, @Param("label") String label);
    @Select("SELECT CAST(pictureId AS CHAR) AS pictureId,label,updateTime FROM agent_feedback "
            + "WHERE taskId=#{taskId} AND userId=#{userId} ORDER BY pictureId LIMIT 20")
    List<Map<String,Object>> list(@Param("taskId") String taskId, @Param("userId") Long userId);
}
