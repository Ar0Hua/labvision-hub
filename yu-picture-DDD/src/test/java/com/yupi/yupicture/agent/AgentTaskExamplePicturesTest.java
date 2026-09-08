package com.yupi.yupicture.agent;

import com.yupi.yupicture.application.agent.*;
import com.yupi.yupicture.domain.agent.AgentMessage;
import com.yupi.yupicture.domain.agent.AgentTask;
import com.yupi.yupicture.domain.user.entity.User;
import com.yupi.yupicture.infrastructure.exception.BusinessException;
import com.yupi.yupicture.infrastructure.mapper.AgentTaskMapper;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.Arrays;
import java.util.Collections;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

class AgentTaskExamplePicturesTest {
    @Test
    void validatesPermissionAndPersistsDeduplicatedExampleIds() {
        AgentTaskService service = new AgentTaskService();
        AgentMessageService messages = mock(AgentMessageService.class);
        AgentPictureService pictures = mock(AgentPictureService.class);
        AgentTaskMapper mapper = mock(AgentTaskMapper.class);
        AgentMessage message = new AgentMessage();
        message.setId("message");
        User user = new User();
        user.setId(7L);
        when(messages.createUserMessage("conversation", "查找相似图片", user)).thenReturn(message);
        when(mapper.insert(any(AgentTask.class))).thenReturn(1);
        ReflectionTestUtils.setField(service, "messages", messages);
        ReflectionTestUtils.setField(service, "pictures", pictures);
        ReflectionTestUtils.setField(service, "mapper", mapper);
        ReflectionTestUtils.setField(service, "events", mock(AgentTaskEventService.class));
        ReflectionTestUtils.setField(service, "publisher", mock(ApplicationEventPublisher.class));

        service.submit("conversation", "查找相似图片", Arrays.asList(11L, 11L, 12L), user);

        verify(pictures).details("conversation", Arrays.asList(11L, 12L), user);
        ArgumentCaptor<AgentTask> captor = ArgumentCaptor.forClass(AgentTask.class);
        verify(mapper).insert(captor.capture());
        assertEquals("[11,12]", captor.getValue().getExamplePictureIdsJson());
    }

    @Test
    void rejectsInvalidOrTooManyExamplesBeforeWritingMessage() {
        AgentTaskService service = new AgentTaskService();
        AgentMessageService messages = mock(AgentMessageService.class);
        ReflectionTestUtils.setField(service, "messages", messages);
        User user = new User();
        assertThrows(BusinessException.class, () -> service.submit(
                "conversation", "query", Arrays.asList(1L, 2L, 3L, 4L, 5L, 6L), user));
        assertThrows(BusinessException.class, () -> service.submit(
                "conversation", "query", Collections.singletonList(-1L), user));
        verifyNoInteractions(messages);
    }
}
