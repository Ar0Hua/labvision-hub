package com.yupi.yupicture.agent;

import com.baomidou.mybatisplus.core.conditions.Wrapper;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.yupi.yupicture.application.agent.*;
import com.yupi.yupicture.domain.picture.entity.Picture;
import com.yupi.yupicture.domain.picture.repository.PictureRepository;
import com.yupi.yupicture.infrastructure.exception.BusinessException;
import com.yupi.yupicture.interfaces.dto.agent.AgentInternalSearchRequest;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;
import java.util.*;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class AgentAspectFilterTest {
    @Test void validatesFiniteOrderedBounds() {
        AgentInternalPictureSearchService service = new AgentInternalPictureSearchService();
        for (Double value : Arrays.asList(0d, 101d, Double.NaN, Double.POSITIVE_INFINITY)) {
            AgentInternalSearchRequest request = new AgentInternalSearchRequest();
            request.setMinAspectRatio(value);
            assertThrows(BusinessException.class, () -> ReflectionTestUtils.invokeMethod(service, "validate", request));
        }
        AgentInternalSearchRequest request = new AgentInternalSearchRequest();
        request.setMinAspectRatio(2d); request.setMaxAspectRatio(1d);
        assertThrows(BusinessException.class, () -> ReflectionTestUtils.invokeMethod(service, "validate", request));
    }

    @Test void bindsRatioWithoutRemovingScope() {
        AgentInternalPictureSearchService service = new AgentInternalPictureSearchService();
        AgentInternalTaskService tasks = mock(AgentInternalTaskService.class);
        PictureRepository pictures = mock(PictureRepository.class);
        when(tasks.context("token", "task")).thenReturn(Collections.singletonMap("spaceId", "9"));
        when(pictures.list(any(Wrapper.class))).thenAnswer(call -> {
            QueryWrapper<Picture> query = call.getArgument(0);
            String sql = query.getSqlSegment();
            assertTrue(sql.contains("spaceId"));
            assertTrue(sql.contains("isDelete"));
            assertTrue(sql.contains("NULLIF(picHeight, 0)"));
            assertTrue(query.getParamNameValuePairs().containsValue(1.5d));
            assertTrue(query.getParamNameValuePairs().containsValue(2d));
            return Collections.emptyList();
        });
        ReflectionTestUtils.setField(service, "internalTasks", tasks);
        ReflectionTestUtils.setField(service, "pictures", pictures);
        AgentInternalSearchRequest request = new AgentInternalSearchRequest();
        request.setMinAspectRatio(1.5d); request.setMaxAspectRatio(2d);
        service.search("token", "task", request);
        verify(pictures).list(any(Wrapper.class));
    }
}
