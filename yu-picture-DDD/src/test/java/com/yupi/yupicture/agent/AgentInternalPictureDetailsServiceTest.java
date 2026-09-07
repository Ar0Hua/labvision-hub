package com.yupi.yupicture.agent;

import com.yupi.yupicture.application.agent.*;
import com.yupi.yupicture.domain.user.entity.User;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.*;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.Mockito.*;

class AgentInternalPictureDetailsServiceTest {
    @Test void qdrantCandidatesAreRecheckedUsingSignedConversationAndUser() {
        AgentInternalPictureDetailsService service = new AgentInternalPictureDetailsService();
        AgentInternalTaskService internal = mock(AgentInternalTaskService.class);
        AgentPictureService pictures = mock(AgentPictureService.class);
        ReflectionTestUtils.setField(service, "internalTasks", internal);
        ReflectionTestUtils.setField(service, "pictures", pictures);
        Map<String,Object> context = new HashMap<>();
        context.put("conversationId", "conversation");
        context.put("userId", "2059881449783808001");
        when(internal.context("Bearer token", "task")).thenReturn(context);
        List<Long> ids = Arrays.asList(2060208764149547009L, 2060208764149547010L);
        when(pictures.details(eq("conversation"), eq(ids), any(User.class)))
                .thenReturn(Collections.singletonList(Collections.singletonMap("pictureId", ids.get(0).toString())));

        List<Map<String,Object>> result = service.details("Bearer token", "task", ids);

        ArgumentCaptor<User> user = ArgumentCaptor.forClass(User.class);
        verify(pictures).details(eq("conversation"), eq(ids), user.capture());
        assertEquals(Long.valueOf(2059881449783808001L), user.getValue().getId());
        assertEquals("2060208764149547009", result.get(0).get("pictureId"));
    }
}
