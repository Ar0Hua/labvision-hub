package com.yupi.yupicture;

import com.yupi.yupicture.application.agent.*;
import com.yupi.yupicture.infrastructure.mapper.AgentTaskMapper;
import com.yupi.yupicture.infrastructure.exception.BusinessException;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;
import java.util.*;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class AgentLateOutputTest {
    @Test void terminalOrQueuedTaskCannotAcceptLateAgentOutput() {
        AgentInternalTaskService service=spy(new AgentInternalTaskService());
        AgentTaskMapper tasks=mock(AgentTaskMapper.class);
        AgentTaskEventService events=mock(AgentTaskEventService.class);
        ReflectionTestUtils.setField(service,"tasks",tasks);
        ReflectionTestUtils.setField(service,"events",events);
        for(String status:Arrays.asList("PENDING","CANCELLED","FAILED","SUCCEEDED")) {
            doReturn(Collections.singletonMap("status",status)).when(service).context("token","task");
            assertThrows(BusinessException.class,()->service.appendEvent("token","task","answer_delta","{}"));
        }
        verifyNoInteractions(events);
        verify(tasks,times(4)).lockById("task");
    }
}
