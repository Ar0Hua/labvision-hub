package com.yupi.yupicture.agent;
import com.yupi.yupicture.application.agent.*;
import com.yupi.yupicture.domain.agent.AgentTask;
import com.yupi.yupicture.infrastructure.mapper.AgentTaskMapper;
import org.junit.jupiter.api.Test;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.test.util.ReflectionTestUtils;
import java.util.*;
import static org.mockito.Mockito.*;
import static org.mockito.ArgumentMatchers.*;
import static org.junit.jupiter.api.Assertions.*;

class AgentTaskRecoveryServiceTest {
    @Test void conditionalClaimPublishesOnlyWonRecoveryAndStopsAtLimit() {
        AgentTaskRecoveryService service=new AgentTaskRecoveryService();
        AgentTaskMapper tasks=mock(AgentTaskMapper.class);
        AgentTaskEventService events=mock(AgentTaskEventService.class);
        ApplicationEventPublisher publisher=mock(ApplicationEventPublisher.class);
        ReflectionTestUtils.setField(service,"tasks",tasks);
        ReflectionTestUtils.setField(service,"events",events);
        ReflectionTestUtils.setField(service,"publisher",publisher);
        AgentTask task=new AgentTask(); task.setId("t"); task.setRetryCount(0);
        when(tasks.selectList(any())).thenReturn(Collections.singletonList(task));
        when(tasks.update(isNull(),any())).thenReturn(0);
        assertEquals(0,service.recover());
        verifyNoInteractions(publisher);
        when(tasks.update(isNull(),any())).thenReturn(1);
        assertEquals(1,service.recover());
        verify(publisher).publishEvent(any(AgentTaskDispatchRequested.class));
        clearInvocations(publisher);
        task.setRetryCount(3);
        assertEquals(0,service.recover());
        verifyNoInteractions(publisher);
        verify(events).append("t","error","{\"code\":\"RECOVERY_EXHAUSTED\"}");
    }
}
