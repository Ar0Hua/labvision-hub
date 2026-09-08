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

import java.time.LocalDateTime;
import java.util.*;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class AgentStructuredPictureSearchTest {
    private static final String TASK = "11111111-1111-1111-1111-111111111111";

    @Test void appliesBoundedTypedFiltersInsideSignedScope() {
        Fixture f = fixture("2060208764149547009");
        when(f.pictures.list(any(Wrapper.class))).thenReturn(Collections.emptyList());
        AgentInternalSearchRequest request = new AgentInternalSearchRequest();
        request.setFormats(Arrays.asList("PNG", "tif"));
        request.setCreatedAfter("2026-05-01");
        request.setCreatedBefore("2026-05-31");
        request.setMinWidth(1920);
        request.setMinHeight(1080);
        request.setMaxSizeBytes(10_485_760L);
        request.setSort("oldest");

        f.service.search("Bearer token", TASK, request);

        ArgumentCaptor<QueryWrapper<Picture>> captor = wrapperCaptor();
        verify(f.pictures).list(captor.capture());
        QueryWrapper<Picture> query = captor.getValue();
        String sql = query.getSqlSegment();
        assertTrue(sql.contains("spaceId"));
        assertTrue(sql.contains("picFormat"));
        assertTrue(sql.contains("createTime"));
        assertTrue(sql.contains("picWidth"));
        assertTrue(sql.contains("picHeight"));
        assertTrue(sql.contains("picSize"));
        assertTrue(sql.contains("ORDER BY createTime ASC,id ASC"));
        Collection<Object> values = query.getParamNameValuePairs().values();
        assertTrue(values.contains("png"));
        assertTrue(values.contains("tif"));
        assertTrue(values.contains(1920));
        assertTrue(values.contains(1080));
        assertTrue(values.contains(10_485_760L));
        assertTrue(values.stream().anyMatch(value -> value instanceof LocalDateTime));
    }

    @Test void rejectsUnknownOrUnboundedFilters() {
        Fixture f = fixture(null);
        AgentInternalSearchRequest request = new AgentInternalSearchRequest();
        request.setFormats(Collections.singletonList("svg"));
        assertThrows(BusinessException.class,
                () -> f.service.search("Bearer token", TASK, request));
        request.setFormats(Collections.singletonList("png"));
        request.setCreatedAfter("2026-06-01");
        request.setCreatedBefore("2026-05-01");
        assertThrows(BusinessException.class,
                () -> f.service.search("Bearer token", TASK, request));
        request.setCreatedAfter(null);
        request.setCreatedBefore(null);
        request.setMinWidth(100001);
        assertThrows(BusinessException.class,
                () -> f.service.search("Bearer token", TASK, request));
        verify(f.pictures, never()).list(any(Wrapper.class));
    }

    private Fixture fixture(String spaceId) {
        Fixture f = new Fixture();
        f.service = new AgentInternalPictureSearchService();
        f.internal = mock(AgentInternalTaskService.class);
        f.pictures = mock(PictureRepository.class);
        Map<String, Object> context = new HashMap<>();
        context.put("spaceId", spaceId);
        when(f.internal.context(anyString(), anyString())).thenReturn(context);
        ReflectionTestUtils.setField(f.service, "internalTasks", f.internal);
        ReflectionTestUtils.setField(f.service, "pictures", f.pictures);
        return f;
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
