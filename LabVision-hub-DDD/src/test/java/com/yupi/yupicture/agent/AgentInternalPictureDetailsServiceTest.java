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
        ReflectionTestUtils.setField(service, "features",
                mock(com.yupi.yupicture.infrastructure.mapper.PictureAiFeatureMapper.class));
        ReflectionTestUtils.setField(service, "sourcePictures",
                mock(com.yupi.yupicture.domain.picture.repository.PictureRepository.class));
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
    @Test void staleFeaturesAreOmittedUntilMatchingVersionIsIndexed() {
        AgentInternalPictureDetailsService service = new AgentInternalPictureDetailsService();
        AgentInternalTaskService internal = mock(AgentInternalTaskService.class);
        AgentPictureService pictures = mock(AgentPictureService.class);
        com.yupi.yupicture.infrastructure.mapper.PictureAiFeatureMapper features =
                mock(com.yupi.yupicture.infrastructure.mapper.PictureAiFeatureMapper.class);
        com.yupi.yupicture.domain.picture.repository.PictureRepository sources =
                mock(com.yupi.yupicture.domain.picture.repository.PictureRepository.class);
        ReflectionTestUtils.setField(service, "internalTasks", internal);
        ReflectionTestUtils.setField(service, "pictures", pictures);
        ReflectionTestUtils.setField(service, "features", features);
        ReflectionTestUtils.setField(service, "sourcePictures", sources);
        Map<String,Object> context = new HashMap<>();
        context.put("conversationId", "c"); context.put("userId", "1");
        when(internal.context("token", "t")).thenReturn(context);
        when(pictures.details(eq("c"), anyList(), any(User.class)))
                .thenReturn(Collections.singletonList(Collections.singletonMap("pictureId", "2")));
        com.yupi.yupicture.domain.picture.entity.Picture source =
                new com.yupi.yupicture.domain.picture.entity.Picture();
        source.setUpdateTime(new Date(2000));
        when(sources.getById(2L)).thenReturn(source);
        com.yupi.yupicture.domain.agent.PictureAiFeature feature =
                new com.yupi.yupicture.domain.agent.PictureAiFeature();
        feature.setIndexStatus("READY"); feature.setSourceUpdatedAt(new Date(1000));
        when(features.selectOne(any())).thenReturn(feature);
        org.junit.jupiter.api.Assertions.assertFalse(
                service.details("token", "t", Collections.singletonList(2L)).get(0).containsKey("features"));
        feature.setSourceUpdatedAt(new Date(2000));
        org.junit.jupiter.api.Assertions.assertTrue(
                service.details("token", "t", Collections.singletonList(2L)).get(0).containsKey("features"));
    }

}
