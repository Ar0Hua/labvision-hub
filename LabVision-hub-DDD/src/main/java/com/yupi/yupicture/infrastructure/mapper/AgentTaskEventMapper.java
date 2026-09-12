package com.yupi.yupicture.infrastructure.mapper;
import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.yupi.yupicture.domain.agent.AgentTaskEvent;
public interface AgentTaskEventMapper extends BaseMapper<AgentTaskEvent> {
    @org.apache.ibatis.annotations.Select("SELECT payloadJson FROM agent_task_event WHERE taskId=#{taskId} AND eventType='citation' ORDER BY id DESC LIMIT 201")
    java.util.List<String> citationPayloads(@org.apache.ibatis.annotations.Param("taskId") String taskId);
}
