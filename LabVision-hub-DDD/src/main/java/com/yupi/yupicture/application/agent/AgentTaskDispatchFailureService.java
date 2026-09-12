package com.yupi.yupicture.application.agent;

import com.baomidou.mybatisplus.core.conditions.update.UpdateWrapper;
import com.yupi.yupicture.domain.agent.AgentTask;
import com.yupi.yupicture.infrastructure.mapper.AgentTaskMapper;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import javax.annotation.Resource;

@Service
public class AgentTaskDispatchFailureService {
    @Resource private AgentTaskMapper tasks;
    @Resource private AgentTaskEventService events;

    @Transactional(rollbackFor = Exception.class)
    public void markFailed(String taskId) {
        int changed = tasks.update(null, new UpdateWrapper<AgentTask>()
                .eq("id", taskId).eq("status", "PENDING")
                .set("status", "FAILED").set("stage", "DISPATCH_FAILED")
                .set("errorCode", "AGENT_SERVICE_UNAVAILABLE")
                .set("errorMessage", "Agent 服务暂时不可用，请稍后重试"));
        if (changed == 1) {
            events.append(taskId, "error",
                    "{\"code\":\"AGENT_SERVICE_UNAVAILABLE\",\"stage\":\"DISPATCH_FAILED\"}");
        }
    }
}
