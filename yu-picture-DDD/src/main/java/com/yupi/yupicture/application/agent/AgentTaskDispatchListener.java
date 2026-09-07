package com.yupi.yupicture.application.agent;

import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Component;
import org.springframework.transaction.event.TransactionPhase;
import org.springframework.transaction.event.TransactionalEventListener;

import javax.annotation.Resource;

@Slf4j
@Component
public class AgentTaskDispatchListener {
    @Resource private AgentTaskDispatchGateway gateway;
    @Resource private AgentTaskDispatchFailureService failures;

    @Async
    @TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT)
    public void onRequested(AgentTaskDispatchRequested event) {
        try {
            gateway.dispatch(event.getTaskId());
        } catch (RuntimeException error) {
            log.warn("Agent task dispatch failed, taskId={}, cause={}",
                    event.getTaskId(), error.getClass().getSimpleName());
            failures.markFailed(event.getTaskId());
        }
    }
}
