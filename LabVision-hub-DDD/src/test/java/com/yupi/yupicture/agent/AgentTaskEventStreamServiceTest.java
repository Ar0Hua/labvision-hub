package com.yupi.yupicture.agent;

import com.yupi.yupicture.application.agent.*;
import com.yupi.yupicture.domain.user.entity.User;
import com.yupi.yupicture.infrastructure.exception.BusinessException;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class AgentTaskEventStreamServiceTest {
    @Test void cursorPrefersLastEventIdAndRejectsInvalidValues() {
        AgentTaskEventStreamService service=new AgentTaskEventStreamService();
        assertEquals(12L,service.parseCursor("12",3L));
        assertEquals(3L,service.parseCursor(null,3L));
        assertEquals(0L,service.parseCursor(" ",null));
        assertThrows(BusinessException.class,()->service.parseCursor("-1",null));
        assertThrows(BusinessException.class,()->service.parseCursor("x",null));
    }

    @Test void authorizationOccursBeforeStreaming() {
        AgentTaskEventStreamService service=new AgentTaskEventStreamService();
        AgentTaskEventService events=mock(AgentTaskEventService.class);
        ReflectionTestUtils.setField(service,"events",events);
        ReflectionTestUtils.setField(service,"tasks",mock(AgentTaskService.class));
        User user=new User(); user.setId(1L);
        service.authorize("task",5L,user);
        verify(events).listAfter("task",5L,1,user);
    }
}
