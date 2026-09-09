package com.yupi.yupicture.agent;

import com.baomidou.mybatisplus.core.conditions.Wrapper;
import com.yupi.yupicture.application.agent.*;
import com.yupi.yupicture.domain.agent.AgentConversation;
import com.yupi.yupicture.domain.agent.AgentTask;
import com.yupi.yupicture.infrastructure.mapper.AgentConversationMapper;
import com.yupi.yupicture.infrastructure.mapper.AgentTaskMapper;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpMethod;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.web.client.RestTemplate;

import java.net.URI;

import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

class AgentTaskDispatchTest {
    private static final String ID = "11111111-1111-1111-1111-111111111111";

    @Test void gatewayPostsSignedTaskAfterRelationshipCheck() {
        AgentTaskDispatchGateway gateway = new AgentTaskDispatchGateway();
        AgentTaskMapper tasks = mock(AgentTaskMapper.class);
        AgentConversationMapper conversations = mock(AgentConversationMapper.class);
        AgentServiceTokenService tokens = mock(AgentServiceTokenService.class);
        RestTemplate client = mock(RestTemplate.class);
        ReflectionTestUtils.setField(gateway, "tasks", tasks);
        ReflectionTestUtils.setField(gateway, "conversations", conversations);
        ReflectionTestUtils.setField(gateway, "tokens", tokens);
        ReflectionTestUtils.setField(gateway, "client", client);
        ReflectionTestUtils.setField(gateway, "baseUrl", "http://127.0.0.1:8000/");
        AgentTask task = task("PENDING");
        when(tasks.selectById(ID)).thenReturn(task);
        when(conversations.selectById("conversation")).thenReturn(conversation());
        when(tokens.issue(ID, "conversation", 7L, 9L, 0)).thenReturn("signed-token");

        gateway.dispatch(ID);

        verify(client).exchange(eq(URI.create("http://127.0.0.1:8000/internal/tasks/" + ID + "/run")),
                eq(HttpMethod.POST), argThat((HttpEntity<Void> request) ->
                        "Bearer signed-token".equals(request.getHeaders().getFirst("Authorization"))), eq(Void.class));
    }

    @Test void gatewaySkipsTaskThatIsNoLongerPending() {
        AgentTaskDispatchGateway gateway = new AgentTaskDispatchGateway();
        AgentTaskMapper tasks = mock(AgentTaskMapper.class);
        RestTemplate client = mock(RestTemplate.class);
        ReflectionTestUtils.setField(gateway, "tasks", tasks);
        ReflectionTestUtils.setField(gateway, "client", client);
        when(tasks.selectById(ID)).thenReturn(task("CANCELLED"));
        gateway.dispatch(ID);
        verifyNoInteractions(client);
    }

    @Test void listenerTurnsDispatchExceptionIntoPersistentFailure() {
        AgentTaskDispatchListener listener = new AgentTaskDispatchListener();
        AgentTaskDispatchGateway gateway = mock(AgentTaskDispatchGateway.class);
        AgentTaskDispatchFailureService failures = mock(AgentTaskDispatchFailureService.class);
        ReflectionTestUtils.setField(listener, "gateway", gateway);
        ReflectionTestUtils.setField(listener, "failures", failures);
        doThrow(new IllegalStateException("offline")).when(gateway).dispatch(ID);
        listener.onRequested(new AgentTaskDispatchRequested(ID));
        verify(failures).markFailed(ID);
    }

    @Test void failureUpdateIsConditionalAndEmitsSafeEvent() {
        AgentTaskDispatchFailureService service = new AgentTaskDispatchFailureService();
        AgentTaskMapper tasks = mock(AgentTaskMapper.class);
        AgentTaskEventService events = mock(AgentTaskEventService.class);
        ReflectionTestUtils.setField(service, "tasks", tasks);
        ReflectionTestUtils.setField(service, "events", events);
        when(tasks.update(isNull(), any(Wrapper.class))).thenReturn(1);
        service.markFailed(ID);
        verify(events).append(ID, "error", "{\"code\":\"AGENT_SERVICE_UNAVAILABLE\",\"stage\":\"DISPATCH_FAILED\"}");

        reset(tasks, events);
        service.markFailed(ID);
        verifyNoInteractions(events);
    }

    private AgentTask task(String status) {
        AgentTask task = new AgentTask();
        task.setId(ID);
        task.setConversationId("conversation");
        task.setUserId(7L);
        task.setStatus(status);
        return task;
    }

    private AgentConversation conversation() {
        AgentConversation conversation = new AgentConversation();
        conversation.setId("conversation");
        conversation.setUserId(7L);
        conversation.setSpaceId(9L);
        conversation.setStatus("ACTIVE");
        return conversation;
    }
}
