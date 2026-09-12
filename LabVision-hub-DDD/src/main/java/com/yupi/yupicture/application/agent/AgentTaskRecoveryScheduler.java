package com.yupi.yupicture.application.agent;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.scheduling.annotation.*;
import org.springframework.stereotype.Component;
import javax.annotation.Resource;

@Component
@EnableScheduling
@ConditionalOnProperty(name="agent.recovery.enabled",havingValue="true")
public class AgentTaskRecoveryScheduler {
    @Resource private AgentTaskRecoveryService recovery;
    @Scheduled(fixedDelayString="${agent.recovery.interval-ms:60000}")
    public void scan() { recovery.recover(); }
}
