package com.yupi.yupicture.agent;

import com.yupi.yupicture.application.agent.AgentConversationService;
import com.yupi.yupicture.domain.agent.AgentConversation;
import com.yupi.yupicture.domain.agent.AgentTask;
import com.yupi.yupicture.domain.user.entity.User;
import com.yupi.yupicture.infrastructure.mapper.AgentConversationMapper;
import com.yupi.yupicture.infrastructure.mapper.AgentTaskMapper;
import com.yupi.yupicture.infrastructure.exception.BusinessException;
import com.baomidou.mybatisplus.core.conditions.update.UpdateWrapper;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;
import static org.mockito.ArgumentMatchers.*;

class AgentConversationManagementTest {
    private AgentConversationService service(AgentConversationMapper mapper, AgentTaskMapper tasks) {
        AgentConversationService service = new AgentConversationService();
        ReflectionTestUtils.setField(service, "mapper", mapper);
        ReflectionTestUtils.setField(service, "taskMapper", tasks);
        return service;
    }
    private User user() { User user = new User(); user.setId(7L); return user; }

    @Test void validatesTitleAndLoginBeforeWriting() {
        AgentConversationMapper mapper = mock(AgentConversationMapper.class);
        AgentConversationService service = service(mapper, mock(AgentTaskMapper.class));
        for (String title : new String[]{null, " ", "x".repeat(61), "a\nb"}) {
            assertThrows(BusinessException.class, () -> service.rename("id", title, user()));
        }
        assertThrows(BusinessException.class, () -> service.rename("id", "test", null));
        assertThrows(BusinessException.class, () -> service.remove("id", null));
        verifyNoInteractions(mapper);
    }
    @Test void renameUsesOwnershipAndActiveStatusAndTrimsTitle() {
        AgentConversationMapper mapper = mock(AgentConversationMapper.class);
        AgentConversationService service = service(mapper, mock(AgentTaskMapper.class));
        when(mapper.update(isNull(), any())).thenReturn(1);
        service.rename("id", "  河道研究  ", user());
        verify(mapper).update(isNull(), argThat(wrapper -> {
            UpdateWrapper<AgentConversation> update = (UpdateWrapper<AgentConversation>) wrapper;
            String sql = update.getSqlSegment();
            return sql.contains("userId") && sql.contains("status") && update.getParamNameValuePairs().containsValue("河道研究");
        }));
    }
    @Test void forbiddenDeletionDoesNotTouchTasks() {
        AgentConversationMapper mapper = mock(AgentConversationMapper.class);
        AgentTaskMapper tasks = mock(AgentTaskMapper.class);
        AgentConversationService service = service(mapper, tasks);
        assertThrows(BusinessException.class, () -> service.remove("other-user-conversation", user()));
        verifyNoInteractions(tasks);
    }
    @Test void deletionOnlyCancelsOwnedActiveTasks() {
        AgentConversationMapper mapper = mock(AgentConversationMapper.class);
        AgentTaskMapper tasks = mock(AgentTaskMapper.class);
        when(mapper.update(isNull(), any())).thenReturn(1);
        service(mapper, tasks).remove("id", user());
        verify(tasks).update(isNull(), argThat(wrapper -> {
            UpdateWrapper<AgentTask> update = (UpdateWrapper<AgentTask>) wrapper;
            String sql = update.getSqlSegment();
            return sql.contains("conversationId") && sql.contains("userId") && sql.contains("status IN")
                    && update.getParamNameValuePairs().containsValue("CANCELLED");
        }));
    }
}
