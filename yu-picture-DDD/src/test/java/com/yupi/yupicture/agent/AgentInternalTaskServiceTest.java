package com.yupi.yupicture.agent;

import com.baomidou.mybatisplus.core.conditions.Wrapper;
import com.yupi.yupicture.application.agent.*;
import com.yupi.yupicture.domain.agent.*;
import com.yupi.yupicture.domain.user.entity.User;
import com.yupi.yupicture.domain.user.repository.UserRepository;
import com.yupi.yupicture.infrastructure.exception.BusinessException;
import com.yupi.yupicture.infrastructure.mapper.*;
import com.yupi.yupicture.interfaces.dto.agent.AgentInternalStateRequest;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;
import java.util.*;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class AgentInternalTaskServiceTest {
    @Test void contextRechecksSignedIdentityDatabaseRelationsAndSpaceAccess() {
        Fixture f=fixture();
        Map<String,Object> context=f.service.context("Bearer token","task");
        assertEquals("query",context.get("query"));
        assertEquals("9",context.get("spaceId"));
        verify(f.access).resolve(f.user,Collections.singletonList(9L));

        f.signed.setUserId("2");
        assertThrows(BusinessException.class,()->f.service.context("Bearer token","task"));
        assertThrows(BusinessException.class,()->f.service.context("token","task"));
    }

    @Test void stateTransitionsAreConditionalAndEmitPublicEvent() {
        Fixture f=fixture();
        when(f.tasks.update(isNull(),any(Wrapper.class))).thenReturn(1);
        AgentInternalStateRequest running=new AgentInternalStateRequest();
        running.setStatus("RUNNING"); running.setStage("retrieving");
        f.service.updateState("Bearer token","task",running);
        verify(f.events).append("task","status","{\"status\":\"RUNNING\",\"stage\":\"retrieving\"}");

        AgentInternalStateRequest invalid=new AgentInternalStateRequest();
        invalid.setStatus("CANCELLED"); invalid.setStage("cancelled");
        assertThrows(BusinessException.class,()->f.service.updateState("Bearer token","task",invalid));
        running.setStage("bad stage");
        assertThrows(BusinessException.class,()->f.service.updateState("Bearer token","task",running));
    }

    @Test void eventWriteRequiresFreshContext() {
        Fixture f=fixture();
        f.service.appendEvent("Bearer token","task","citation","{}");
        verify(f.events).append("task","citation","{}");
        when(f.conversations.selectById("conversation")).thenReturn(null);
        assertThrows(BusinessException.class,
                ()->f.service.appendEvent("Bearer token","task","citation","{}"));
    }

    private Fixture fixture() {
        Fixture f=new Fixture();
        f.service=new AgentInternalTaskService();
        f.tokens=mock(AgentServiceTokenService.class);
        f.tasks=mock(AgentTaskMapper.class);
        f.conversations=mock(AgentConversationMapper.class);
        f.messages=mock(AgentMessageMapper.class);
        f.users=mock(UserRepository.class);
        f.access=mock(AgentAccessService.class);
        f.events=mock(AgentTaskEventService.class);
        ReflectionTestUtils.setField(f.service,"tokens",f.tokens);
        ReflectionTestUtils.setField(f.service,"tasks",f.tasks);
        ReflectionTestUtils.setField(f.service,"conversations",f.conversations);
        ReflectionTestUtils.setField(f.service,"messages",f.messages);
        ReflectionTestUtils.setField(f.service,"users",f.users);
        ReflectionTestUtils.setField(f.service,"access",f.access);
        ReflectionTestUtils.setField(f.service,"events",f.events);
        f.signed=new AgentServiceContext(); f.signed.setTaskId("task");
        f.signed.setConversationId("conversation"); f.signed.setUserId("1"); f.signed.setSpaceId("9");
        when(f.tokens.verify("token","task")).thenReturn(f.signed);
        AgentTask task=new AgentTask(); task.setId("task"); task.setConversationId("conversation");
        task.setInputMessageId("message"); task.setUserId(1L);
        when(f.tasks.selectById("task")).thenReturn(task);
        AgentConversation conversation=new AgentConversation(); conversation.setId("conversation");
        conversation.setUserId(1L); conversation.setSpaceId(9L); conversation.setStatus("ACTIVE");
        when(f.conversations.selectById("conversation")).thenReturn(conversation);
        AgentMessage message=new AgentMessage(); message.setId("message");
        message.setConversationId("conversation"); message.setContent("query");
        when(f.messages.selectById("message")).thenReturn(message);
        f.user=new User(); f.user.setId(1L); f.user.setIsDelete(0);
        when(f.users.getById(1L)).thenReturn(f.user);
        return f;
    }

    private static class Fixture {
        AgentInternalTaskService service; AgentServiceTokenService tokens;
        AgentTaskMapper tasks; AgentConversationMapper conversations;
        AgentMessageMapper messages; UserRepository users; AgentAccessService access;
        AgentTaskEventService events; AgentServiceContext signed; User user;
    }
}
