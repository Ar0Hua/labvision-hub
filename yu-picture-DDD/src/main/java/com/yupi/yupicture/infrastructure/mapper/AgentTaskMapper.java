package com.yupi.yupicture.infrastructure.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.yupi.yupicture.domain.agent.AgentTask;

public interface AgentTaskMapper extends BaseMapper<AgentTask> {
    @org.apache.ibatis.annotations.Select("SELECT * FROM agent_task WHERE id=#{id} FOR UPDATE")
    AgentTask lockById(@org.apache.ibatis.annotations.Param("id") String id);
}
