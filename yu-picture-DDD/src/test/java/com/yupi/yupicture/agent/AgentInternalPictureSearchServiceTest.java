package com.yupi.yupicture.agent;

import com.baomidou.mybatisplus.core.conditions.Wrapper;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.yupi.yupicture.application.agent.AgentInternalPictureSearchService;
import com.yupi.yupicture.application.agent.AgentInternalTaskService;
import com.yupi.yupicture.domain.picture.entity.Picture;
import com.yupi.yupicture.domain.picture.repository.PictureRepository;
import com.yupi.yupicture.infrastructure.exception.BusinessException;
import com.yupi.yupicture.interfaces.dto.agent.AgentInternalSearchRequest;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.*;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class AgentInternalPictureSearchServiceTest {
    private static final String TASK = "11111111-1111-1111-1111-111111111111";

    @Test void publicConversationSearchIsReviewedAndNeverReturnsUrl() {
        Fixture f = fixture(null);
        Picture picture = picture(null);
        picture.setUrl("https://private.example/original.png");
        when(f.pictures.list(any(Wrapper.class))).thenReturn(Collections.singletonList(picture));
        AgentInternalSearchRequest request = new AgentInternalSearchRequest();
        request.setSearchText("显微");
        request.setLimit(10);

        List<Map<String,Object>> result = f.service.search("Bearer token", TASK, request);

        assertEquals("2059881449783808001", result.get(0).get("pictureId"));
        assertFalse(result.get(0).containsKey("url"));
        ArgumentCaptor<QueryWrapper<Picture>> captor = wrapperCaptor();
        verify(f.pictures).list(captor.capture());
        String sql = captor.getValue().getSqlSegment();
        assertTrue(sql.contains("spaceId IS NULL"));
        assertTrue(sql.contains("reviewStatus"));
        verify(f.internal).context("Bearer token", TASK);
    }

    @Test void privateConversationForcesSignedSpaceAndBoundsInput() {
        Fixture f = fixture("2060208764149547009");
        when(f.pictures.list(any(Wrapper.class))).thenReturn(Collections.emptyList());
        AgentInternalSearchRequest request = new AgentInternalSearchRequest();
        request.setCategory("实验仪器");
        request.setTags(Arrays.asList("显微成像", "标定"));
        request.setLimit(20);
        f.service.search("Bearer token", TASK, request);
        ArgumentCaptor<QueryWrapper<Picture>> captor = wrapperCaptor();
        verify(f.pictures).list(captor.capture());
        assertTrue(captor.getValue().getSqlSegment().contains("spaceId"));
        Collection<Object> values = captor.getValue().getParamNameValuePairs().values();
        assertTrue(values.stream().anyMatch(value ->
                "2060208764149547009".equals(String.valueOf(value))));
        assertTrue(values.contains("实验仪器"));

        request.setLimit(21);
        assertThrows(BusinessException.class, () -> f.service.search("Bearer token", TASK, request));
    }

    private Fixture fixture(String spaceId) {
        Fixture f = new Fixture();
        f.service = new AgentInternalPictureSearchService();
        f.internal = mock(AgentInternalTaskService.class);
        f.pictures = mock(PictureRepository.class);
        Map<String,Object> context = new HashMap<>();
        context.put("spaceId", spaceId);
        when(f.internal.context(anyString(), anyString())).thenReturn(context);
        ReflectionTestUtils.setField(f.service, "internalTasks", f.internal);
        ReflectionTestUtils.setField(f.service, "pictures", f.pictures);
        return f;
    }

    private Picture picture(Long spaceId) {
        Picture picture = new Picture();
        picture.setId(2059881449783808001L);
        picture.setSpaceId(spaceId);
        picture.setName("显微成像");
        picture.setTags("[\"显微成像\"]");
        return picture;
    }

    @SuppressWarnings({"unchecked", "rawtypes"})
    private ArgumentCaptor<QueryWrapper<Picture>> wrapperCaptor() {
        return (ArgumentCaptor) ArgumentCaptor.forClass(Wrapper.class);
    }

    private static class Fixture {
        AgentInternalPictureSearchService service;
        AgentInternalTaskService internal;
        PictureRepository pictures;
    }
}
