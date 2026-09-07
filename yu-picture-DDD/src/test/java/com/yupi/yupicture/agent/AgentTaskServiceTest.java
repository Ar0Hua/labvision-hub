package com.yupi.yupicture.agent;

import com.yupi.yupicture.application.agent.*;
import com.yupi.yupicture.domain.agent.*;
import com.yupi.yupicture.domain.user.entity.User;
import com.yupi.yupicture.infrastructure.exception.*;
import com.yupi.yupicture.infrastructure.mapper.AgentTaskMapper;
import com.yupi.yupicture.interfaces.vo.agent.AgentTaskVO;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.test.util.ReflectionTestUtils;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;
import java.util.*;

class AgentTaskServiceTest {
    @Test void submitCreatesPendingTaskForSavedMessage() {
        AgentTaskService service = service();
        AgentMessageService messages = field(service, "messages");
        AgentTaskMapper mapper = field(service, "mapper");
        User user = user(7L);
        AgentMessage message = new AgentMessage();
        message.setId("message-id");
        when(messages.createUserMessage("conversation", "find images", user)).thenReturn(message);
        when(mapper.insert(any(AgentTask.class))).thenReturn(1);

        AgentTaskVO result = service.submit("conversation", "find images", user);

        ArgumentCaptor<AgentTask> captor = ArgumentCaptor.forClass(AgentTask.class);
        verify(mapper).insert(captor.capture());
        AgentTask saved = captor.getValue();
        assertEquals("PENDING", saved.getStatus());
        assertEquals("QUEUED", saved.getStage());
        assertEquals("message-id", saved.getInputMessageId());
        assertEquals(Long.valueOf(7), saved.getUserId());
        assertEquals(saved.getId(), result.getTaskId());
        ApplicationEventPublisher publisher = field(service, "publisher");
        verify(publisher).publishEvent(any(AgentTaskDispatchRequested.class));
    }

    @Test void failedTaskInsertIsReportedForTransactionRollback() {
        AgentTaskService service = service();
        AgentMessageService messages = field(service, "messages");
        AgentTaskMapper mapper = field(service, "mapper");
        User user = user(1L);
        AgentMessage message = new AgentMessage();
        message.setId("message-id");
        when(messages.createUserMessage(anyString(), anyString(), eq(user))).thenReturn(message);
        assertThrows(BusinessException.class, () -> service.submit("c", "query", user));
    }

    @Test void taskReadChecksConversationOwnerAndHidesInternalUserId() {
        AgentTaskService service = service();
        AgentConversationService conversations = field(service, "conversations");
        AgentTaskMapper mapper = field(service, "mapper");
        User user = user(1L);
        String id = "11111111-1111-1111-1111-111111111111";
        AgentTask task = new AgentTask();
        task.setId(id);
        task.setConversationId("conversation");
        task.setUserId(1L);
        when(mapper.selectById(id)).thenReturn(task);
        AgentTaskVO result = service.get(id, user);
        assertEquals(id, result.getTaskId());
        verify(conversations).requireOwner("conversation", user);

        clearInvocations(mapper);
        assertThrows(BusinessException.class, () -> service.get("invalid", user));
        verifyNoInteractions(mapper);
        when(mapper.selectById(id)).thenReturn(null);
        assertThrows(BusinessException.class, () -> service.get(id, user));
    }

    @Test void listByConversationChecksOwnerAndReturnsBoundedTaskViews() {
        AgentTaskService service = service();
        AgentConversationService conversations = field(service, "conversations");
        AgentTaskMapper mapper = field(service, "mapper");
        User user = user(7L);
        AgentTask task = new AgentTask(); task.setId("task"); task.setConversationId("conversation");
        when(mapper.selectList(any())).thenReturn(Collections.singletonList(task));

        java.util.List<AgentTaskVO> result = service.listByConversation("conversation", user);

        assertEquals(1, result.size()); assertEquals("task", result.get(0).getTaskId());
        verify(conversations).requireOwner("conversation", user);
        verify(mapper).selectList(argThat(query -> query.getSqlSegment().contains("conversationId")
                && query.getSqlSegment().contains("createTime")));
    }

    private AgentTaskService service() {
        AgentTaskService service = new AgentTaskService();
        ReflectionTestUtils.setField(service, "conversations", mock(AgentConversationService.class));
        ReflectionTestUtils.setField(service, "messages", mock(AgentMessageService.class));
        ReflectionTestUtils.setField(service, "mapper", mock(AgentTaskMapper.class));
        ReflectionTestUtils.setField(service, "events", mock(AgentTaskEventService.class));
        ReflectionTestUtils.setField(service, "publisher", mock(ApplicationEventPublisher.class));
        return service;
    }

    @SuppressWarnings("unchecked")
    private <T> T field(Object target, String name) {
        return (T) ReflectionTestUtils.getField(target, name);
    }

    private User user(long id) {
        User user = new User();
        user.setId(id);
        return user;
    }
}
