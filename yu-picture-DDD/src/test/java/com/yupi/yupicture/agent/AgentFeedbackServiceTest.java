package com.yupi.yupicture.agent;
import com.yupi.yupicture.application.agent.*;
import com.yupi.yupicture.domain.agent.AgentTaskEvent;
import com.yupi.yupicture.domain.user.entity.User;
import com.yupi.yupicture.infrastructure.mapper.*;
import com.yupi.yupicture.infrastructure.exception.BusinessException;
import com.yupi.yupicture.interfaces.vo.agent.AgentTaskVO;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;
import java.util.*;
import static org.mockito.Mockito.*;
import static org.mockito.ArgumentMatchers.*;
import static org.junit.jupiter.api.Assertions.*;

class AgentFeedbackServiceTest {
    @Test void feedbackRequiresTaskCitationAndRechecksNormalPictureAccess() {
        AgentFeedbackService service = new AgentFeedbackService();
        AgentTaskService tasks = mock(AgentTaskService.class);
        AgentPictureService pictures = mock(AgentPictureService.class);
        AgentTaskEventMapper events = mock(AgentTaskEventMapper.class);
        AgentFeedbackMapper feedback = mock(AgentFeedbackMapper.class);
        ReflectionTestUtils.setField(service,"tasks",tasks);
        ReflectionTestUtils.setField(service,"pictures",pictures);
        ReflectionTestUtils.setField(service,"events",events);
        ReflectionTestUtils.setField(service,"feedback",feedback);
        User user = new User(); user.setId(1L);
        AgentTaskVO task = new AgentTaskVO(); task.setConversationId("c");
        when(tasks.get("t",user)).thenReturn(task);
        when(events.selectList(any())).thenReturn(Collections.emptyList());
        assertThrows(BusinessException.class,()->service.save("t",2L,"relevant",user));
        verifyNoInteractions(feedback);
        AgentTaskEvent event = new AgentTaskEvent();
        event.setPayloadJson("{\"pictureId\":\"2\"}");
        when(events.selectList(any())).thenReturn(Collections.singletonList(event));
        service.save("t",2L,"relevant",user);
        verify(pictures).details("c",Collections.singletonList(2L),user);
        verify(feedback).save("t",1L,2L,"relevant");
        clearInvocations(pictures);
        service.save("t",2L,"permission_issue",user);
        verifyNoInteractions(pictures);
        assertThrows(BusinessException.class,()->service.save("t",2L,"invalid",user));
    }
}
