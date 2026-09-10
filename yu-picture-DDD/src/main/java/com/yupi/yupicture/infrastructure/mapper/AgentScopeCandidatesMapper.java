package com.yupi.yupicture.infrastructure.mapper;
import org.apache.ibatis.annotations.*;
import java.util.List;

public interface AgentScopeCandidatesMapper {
    @Select("SELECT s.id FROM space s WHERE s.isDelete=0 AND (s.userId=#{userId}"
            + " OR (#{admin}=true AND s.spaceType=0)"
            + " OR EXISTS (SELECT 1 FROM space_user su WHERE su.spaceId=s.id AND su.userId=#{userId}))"
            + " ORDER BY s.id LIMIT 501")
    List<Long> candidates(@Param("userId") Long userId,@Param("admin") boolean admin);
}
