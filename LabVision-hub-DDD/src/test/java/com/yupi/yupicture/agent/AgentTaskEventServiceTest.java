package com.yupi.yupicture.agent;

import com.baomidou.mybatisplus.core.conditions.Wrapper;
import com.yupi.yupicture.application.agent.*;
import com.yupi.yupicture.domain.agent.*;
import com.yupi.yupicture.domain.user.entity.User;
import com.yupi.yupicture.infrastructure.exception.BusinessException;
import com.yupi.yupicture.infrastructure.mapper.*;
import com.yupi.yupicture.interfaces.vo.agent.AgentTaskEventVO;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;
import java.util.*;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class AgentTaskEventServiceTest {
    private static final String TASK_ID = "11111111-1111-1111-1111-111111111111";

    @Test void appendAllowsOnlyKnownTypesAndValidJson() {
        Fixture f=fixture();
        when(f.events.insert(any(AgentTaskEvent.class))).thenReturn(1);
        assertEquals("status", f.service.append(TASK_ID,"status","{\"stage\":\"queued\"}").getEventType());
        assertThrows(BusinessException.class,()->f.service.append(TASK_ID,"hidden_thought","{}"));
        assertThrows(BusinessException.class,()->f.service.append(TASK_ID,"status","not-json"));
        assertThrows(BusinessException.class,()->f.service.append("invalid","status","{}"));
    }

    @Test @SuppressWarnings("unchecked")
    void incrementalReadChecksOwnershipAndReturnsStringCursor() {
        Fixture f=fixture();
        AgentTask task=new AgentTask(); task.setConversationId("conversation"); task.setInputMessageId("input");
        when(f.tasks.selectById(TASK_ID)).thenReturn(task);
        AgentTaskEvent event=new AgentTaskEvent(); event.setId(2059881449783808001L);
        event.setEventType("citation"); event.setPayloadJson("{}");
        when(f.events.selectList(any(Wrapper.class))).thenReturn(Collections.singletonList(event));
        User user=new User(); user.setId(1L);
        List<AgentTaskEventVO> result=f.service.listAfter(TASK_ID,10L,50,user);
        assertEquals("2059881449783808001",result.get(0).getEventId());
        verify(f.conversations).requireOwner("conversation",user);
        assertThrows(BusinessException.class,()->f.service.listAfter(TASK_ID,-1L,50,user));
        assertThrows(BusinessException.class,()->f.service.listAfter(TASK_ID,0L,201,user));
    }

    @Test void missingTaskDoesNotQueryEvents() {
        Fixture f=fixture();
        User user=new User(); user.setId(1L);
        assertThrows(BusinessException.class,()->f.service.listAfter(TASK_ID,0L,10,user));
        verifyNoInteractions(f.events);
    }

    @Test void revokedComparisonScopeBlocksEventReplay() {
        Fixture f=fixture();
        AgentTask task=new AgentTask(); task.setConversationId("conversation"); task.setInputMessageId("input");
        when(f.tasks.selectById(TASK_ID)).thenReturn(task);
        AgentMessageMapper messages=(AgentMessageMapper)ReflectionTestUtils.getField(f.service,"messages");
        AgentMessage input=new AgentMessage(); input.setConversationId("conversation"); input.setContent("比较空间 9、10 的图片数量");
        when(messages.selectById("input")).thenReturn(input);
        AgentAccessService access=(AgentAccessService)ReflectionTestUtils.getField(f.service,"access");
        User user=new User(); user.setId(1L);
        when(access.resolve(user,Arrays.asList(9L,10L))).thenThrow(new BusinessException(
                com.yupi.yupicture.infrastructure.exception.ErrorCode.NO_AUTH_ERROR,"权限已撤销"));
        assertThrows(BusinessException.class,()->f.service.listAfter(TASK_ID,0L,50,user));
        verifyNoInteractions(f.events);
    }

    private Fixture fixture() {
        Fixture f=new Fixture();
        f.service=new AgentTaskEventService();
        f.events=mock(AgentTaskEventMapper.class);
        f.tasks=mock(AgentTaskMapper.class);
        f.conversations=mock(AgentConversationService.class);
        ReflectionTestUtils.setField(f.service,"mapper",f.events);
        ReflectionTestUtils.setField(f.service,"tasks",f.tasks);
        ReflectionTestUtils.setField(f.service,"conversations",f.conversations);
        AgentMessageMapper messages=mock(AgentMessageMapper.class);
        AgentMessage input=new AgentMessage(); input.setConversationId("conversation"); input.setContent("query");
        when(messages.selectById("input")).thenReturn(input);
        ReflectionTestUtils.setField(f.service,"messages",messages);
        ReflectionTestUtils.setField(f.service,"access",mock(AgentAccessService.class));
        return f;
    }
    private static class Fixture {
        AgentTaskEventService service; AgentTaskEventMapper events;
        AgentTaskMapper tasks; AgentConversationService conversations;
    }
}
