package com.yupi.yupicture.application.agent;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.UpdateWrapper;
import com.yupi.yupicture.domain.agent.AgentTask;
import com.yupi.yupicture.infrastructure.mapper.AgentTaskMapper;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.context.ApplicationEventPublisher;
import javax.annotation.Resource;
import java.util.*;

@Service
public class AgentTaskRecoveryService {
    @Resource private AgentTaskMapper tasks;
    @Resource private AgentTaskEventService events;
    @Resource private ApplicationEventPublisher publisher;

    @Transactional(rollbackFor=Exception.class)
    public int recover() {
        Date cutoff = new Date(System.currentTimeMillis()-600_000L);
        List<AgentTask> abandoned = tasks.selectList(new QueryWrapper<AgentTask>()
                .in("status","PENDING","RUNNING").lt("updateTime",cutoff)
                .orderByAsc("updateTime").last("LIMIT 50"));
        int recovered=0;
        for (AgentTask task : abandoned) {
            int attempt=task.getRetryCount()==null?0:task.getRetryCount();
            boolean exhausted=attempt>=3;
            UpdateWrapper<AgentTask> update=new UpdateWrapper<AgentTask>()
                    .eq("id",task.getId()).in("status","PENDING","RUNNING")
                    .lt("updateTime",cutoff)
                    .apply("COALESCE(retryCount,0)={0}",attempt)
                    .set("retryCount",attempt+1)
                    .set("updateTime",new Date())
                    .set("status",exhausted?"FAILED":"PENDING")
                    .set("stage",exhausted?"RECOVERY_EXHAUSTED":"QUEUED")
                    .set("errorCode",exhausted?"RECOVERY_EXHAUSTED":null)
                    .set("errorMessage",exhausted?"自动恢复次数已用尽，请检查服务后手动重试":null);
            if (tasks.update(null,update)!=1) continue;
            if (exhausted) {
                events.append(task.getId(),"error","{\"code\":\"RECOVERY_EXHAUSTED\"}");
            } else {
                events.append(task.getId(),"status","{\"stage\":\"recovery_queued\"}");
                publisher.publishEvent(new AgentTaskDispatchRequested(task.getId()));
                recovered++;
            }
        }
        return recovered;
    }
}
