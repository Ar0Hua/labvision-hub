package com.yupi.yupicture.agent;

import com.baomidou.mybatisplus.core.conditions.Wrapper;
import com.yupi.yupicture.application.agent.*;
import com.yupi.yupicture.domain.agent.AgentTask;
import com.yupi.yupicture.domain.user.entity.User;
import com.yupi.yupicture.infrastructure.exception.BusinessException;
import com.yupi.yupicture.infrastructure.mapper.AgentTaskMapper;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.context.ApplicationEventPublisher;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class AgentTaskLifecycleTest {
    private static final String ID = "11111111-1111-1111-1111-111111111111";

    @Test void cancelAndResumeUseConditionalUpdates() {
        Fixture f = fixture("RUNNING");
        AgentTask cancelled = task("CANCELLED");
        when(f.mapper.update(isNull(), any(Wrapper.class))).thenReturn(1);
        when(f.mapper.selectById(ID)).thenReturn(f.task, cancelled);
        assertEquals("CANCELLED", f.service.cancel(ID, f.user).getStatus());
        verify(f.mapper).update(isNull(), any(Wrapper.class));
        verify(f.events).append(ID,"status","{\"status\":\"CANCELLED\",\"stage\":\"CANCELLED\"}");

        reset(f.mapper);
        AgentTask failed = task("FAILED");
        failed.setRetryCount(2);
        AgentTask queued = task("PENDING");
        queued.setStage("QUEUED");
        queued.setRetryCount(3);
        when(f.mapper.selectById(ID)).thenReturn(failed, queued);
        when(f.mapper.update(isNull(), any(Wrapper.class))).thenReturn(1);
        assertEquals(Integer.valueOf(3), f.service.resume(ID, f.user).getRetryCount());
    }

    @Test void terminalCancelIsIdempotentAndInvalidTransitionsFail() {
        Fixture f = fixture("CANCELLED");
        when(f.mapper.selectById(ID)).thenReturn(f.task);
        assertEquals("CANCELLED", f.service.cancel(ID, f.user).getStatus());
        verify(f.mapper, never()).update(any(), any());

        f.task.setStatus("SUCCEEDED");
        when(f.mapper.update(isNull(), any(Wrapper.class))).thenReturn(0);
        assertThrows(BusinessException.class, () -> f.service.cancel(ID, f.user));
        assertThrows(BusinessException.class, () -> f.service.resume(ID, f.user));
    }

    @Test void concurrentStateChangeIsReported() {
        Fixture f = fixture("RUNNING");
        when(f.mapper.selectById(ID)).thenReturn(f.task);
        when(f.mapper.update(isNull(), any(Wrapper.class))).thenReturn(0);
        assertThrows(BusinessException.class, () -> f.service.cancel(ID, f.user));
    }

    private Fixture fixture(String status) {
        Fixture f = new Fixture();
        f.service = new AgentTaskService();
        f.mapper = mock(AgentTaskMapper.class);
        f.conversations = mock(AgentConversationService.class);
        ReflectionTestUtils.setField(f.service, "mapper", f.mapper);
        ReflectionTestUtils.setField(f.service, "conversations", f.conversations);
        ReflectionTestUtils.setField(f.service, "messages", mock(AgentMessageService.class));
        f.events = mock(AgentTaskEventService.class);
        ReflectionTestUtils.setField(f.service, "events", f.events);
        ReflectionTestUtils.setField(f.service, "publisher", mock(ApplicationEventPublisher.class));
        f.user = new User(); f.user.setId(1L);
        f.task = task(status);
        return f;
    }

    private AgentTask task(String status) {
        AgentTask task = new AgentTask();
        task.setId(ID);
        task.setConversationId("conversation");
        task.setStatus(status);
        task.setStage(status);
        task.setRetryCount(0);
        return task;
    }

    private static class Fixture {
        AgentTaskService service;
        AgentTaskMapper mapper;
        AgentConversationService conversations;
        AgentTaskEventService events;
        AgentTask task;
        User user;
    }
}
