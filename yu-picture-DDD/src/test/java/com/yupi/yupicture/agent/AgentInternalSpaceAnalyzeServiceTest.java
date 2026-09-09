package com.yupi.yupicture.agent;

import com.yupi.yupicture.application.agent.AgentInternalSpaceAnalyzeService;
import com.yupi.yupicture.application.agent.AgentInternalTaskService;
import com.yupi.yupicture.application.service.SpaceAnalyzeApplicationService;
import com.yupi.yupicture.domain.user.entity.User;
import com.yupi.yupicture.domain.user.repository.UserRepository;
import com.yupi.yupicture.infrastructure.exception.BusinessException;
import com.yupi.yupicture.interfaces.dto.space.analyze.*;
import com.yupi.yupicture.interfaces.vo.space.analyze.*;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.test.util.ReflectionTestUtils;

import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.*;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class AgentInternalSpaceAnalyzeServiceTest {
    @Test void usesSignedTaskScopeAndReturnsBoundedDeterministicSummary() {
        AgentInternalSpaceAnalyzeService service = new AgentInternalSpaceAnalyzeService();
        AgentInternalTaskService internal = mock(AgentInternalTaskService.class);
        UserRepository users = mock(UserRepository.class);
        SpaceAnalyzeApplicationService analyze = mock(SpaceAnalyzeApplicationService.class);
        ReflectionTestUtils.setField(service, "internalTasks", internal);
        ReflectionTestUtils.setField(service, "users", users);
        ReflectionTestUtils.setField(service, "analyze", analyze);
        ReflectionTestUtils.setField(service, "clock",
                Clock.fixed(Instant.parse("2026-09-09T00:00:00Z"), ZoneOffset.UTC));

        Map<String, Object> context = new HashMap<>();
        context.put("userId", "2059881449783808001");
        context.put("spaceId", "2060208764149547009");
        when(internal.context("Bearer token", "task")).thenReturn(context);
        User user = new User();
        user.setId(2059881449783808001L);
        user.setIsDelete(0);
        when(users.getById(user.getId())).thenReturn(user);

        SpaceUsageAnalyzeResponse usage = new SpaceUsageAnalyzeResponse();
        usage.setUsedCount(30L);
        usage.setUsedSize(4096L);
        when(analyze.getSpaceUsageAnalyze(any(), same(user))).thenReturn(usage);
        List<SpaceCategoryAnalyzeResponse> categories = new ArrayList<>();
        List<SpaceTagAnalyzeResponse> tags = new ArrayList<>();
        List<SpaceUserAnalyzeResponse> trend = new ArrayList<>();
        for (int index = 0; index < 30; index++) {
            categories.add(new SpaceCategoryAnalyzeResponse("分类" + index, (long) index, 100L));
            tags.add(new SpaceTagAnalyzeResponse("标签" + index, (long) (30 - index)));
            trend.add(new SpaceUserAnalyzeResponse("2024-" + index, (long) index));
        }
        when(analyze.getSpaceCategoryAnalyze(any(), same(user))).thenReturn(categories);
        when(analyze.getSpaceTagAnalyze(any(), same(user))).thenReturn(tags);
        when(analyze.getSpaceSizeAnalyze(any(), same(user))).thenReturn(Collections.singletonList(
                new SpaceSizeAnalyzeResponse("<100KB", 3L)));
        when(analyze.getSpaceUserAnalyze(any(), same(user))).thenReturn(trend);

        Map<String, Object> result = service.summary("Bearer token", "task");

        assertEquals("2026-09-09T00:00:00Z", result.get("capturedAt"));
        assertEquals(usage, result.get("usage"));
        Map<?, ?> scope = (Map<?, ?>) result.get("scope");
        assertEquals("space", scope.get("type"));
        assertEquals("2060208764149547009", scope.get("spaceId"));
        assertEquals(20, ((List<?>) result.get("categoryDistribution")).size());
        assertEquals("分类29", ((SpaceCategoryAnalyzeResponse)
                ((List<?>) result.get("categoryDistribution")).get(0)).getCategory());
        assertEquals(20, ((List<?>) result.get("tagDistribution")).size());
        assertEquals(24, ((List<?>) result.get("monthlyUploadTrend")).size());

        ArgumentCaptor<SpaceUsageAnalyzeRequest> request =
                ArgumentCaptor.forClass(SpaceUsageAnalyzeRequest.class);
        verify(analyze).getSpaceUsageAnalyze(request.capture(), same(user));
        assertEquals(Long.valueOf(2060208764149547009L), request.getValue().getSpaceId());
        assertFalse(request.getValue().isQueryPublic());
        ArgumentCaptor<SpaceUserAnalyzeRequest> trendRequest =
                ArgumentCaptor.forClass(SpaceUserAnalyzeRequest.class);
        verify(analyze).getSpaceUserAnalyze(trendRequest.capture(), same(user));
        assertEquals("month", trendRequest.getValue().getTimeDimension());
    }

    @Test void rejectsUnavailableUserBeforeAnyStatisticsQuery() {
        AgentInternalSpaceAnalyzeService service = new AgentInternalSpaceAnalyzeService();
        AgentInternalTaskService internal = mock(AgentInternalTaskService.class);
        UserRepository users = mock(UserRepository.class);
        SpaceAnalyzeApplicationService analyze = mock(SpaceAnalyzeApplicationService.class);
        ReflectionTestUtils.setField(service, "internalTasks", internal);
        ReflectionTestUtils.setField(service, "users", users);
        ReflectionTestUtils.setField(service, "analyze", analyze);
        Map<String, Object> context = new HashMap<>();
        context.put("userId", "7");
        context.put("spaceId", "9");
        when(internal.context(anyString(), anyString())).thenReturn(context);
        when(users.getById(7L)).thenReturn(null);

        assertThrows(BusinessException.class,
                () -> service.summary("Bearer token", "task"));
        verifyNoInteractions(analyze);
    }
}
