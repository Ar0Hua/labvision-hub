package com.yupi.yupicture.application.agent;

import com.yupi.yupicture.application.service.SpaceAnalyzeApplicationService;
import com.yupi.yupicture.domain.user.entity.User;
import com.yupi.yupicture.domain.user.repository.UserRepository;
import com.yupi.yupicture.infrastructure.exception.ErrorCode;
import com.yupi.yupicture.infrastructure.exception.ThrowUtils;
import com.yupi.yupicture.interfaces.dto.space.analyze.*;
import com.yupi.yupicture.interfaces.vo.space.analyze.*;
import org.springframework.stereotype.Service;

import javax.annotation.Resource;
import java.time.Clock;
import java.time.Instant;
import java.util.*;

/**
 * Agent 空间统计只读工具。统计值只来自现有确定性分析服务，范围只来自已签名任务上下文。
 */
@Service
public class AgentInternalSpaceAnalyzeService {
    private static final int DISTRIBUTION_LIMIT = 20;
    private static final int TREND_LIMIT = 24;

    @Resource private AgentInternalTaskService internalTasks;
    @Resource private UserRepository users;
    @Resource private SpaceAnalyzeApplicationService analyze;
    @Resource private com.yupi.yupicture.infrastructure.mapper.AgentGovernanceMapper governance;
    @Resource private com.yupi.yupicture.infrastructure.mapper.AgentStatisticsWindowMapper windows;
    @Resource private AgentAccessService access;
    private Clock clock = Clock.systemUTC();

    public Map<String, Object> summary(String bearerToken, String taskId) {
        return summarizeContext(internalTasks.context(bearerToken, taskId));
    }

    public List<Map<String,Object>> compare(String bearerToken, String taskId) {
        Map<String,Object> context=internalTasks.context(bearerToken,taskId);
        List<Long> ids=AgentExplicitScopes.comparison((String)context.get("query"));
        if(ids.isEmpty()) throw new com.yupi.yupicture.infrastructure.exception.BusinessException(
                ErrorCode.PARAMS_ERROR,"当前任务没有明确请求多空间比较");
        User user=users.getById(Long.valueOf(context.get("userId").toString()));
        access.resolve(user,ids);
        List<Map<String,Object>> result=new ArrayList<>();
        for(Long id:ids) {
            Map<String,Object> scoped=new LinkedHashMap<>(context);
            scoped.put("spaceId",id.toString());
            result.add(summarizeContext(scoped));
        }
        access.resolve(user,ids);
        return result;
    }

    private Map<String,Object> summarizeContext(Map<String,Object> context) {
        User user = users.getById(Long.valueOf(context.get("userId").toString()));
        ThrowUtils.throwIf(user == null || !Integer.valueOf(0).equals(user.getIsDelete()),
                ErrorCode.NO_AUTH_ERROR, "Agent 统计用户不可用");
        Object rawSpaceId = context.get("spaceId");

        SpaceUsageAnalyzeRequest usageRequest = scoped(new SpaceUsageAnalyzeRequest(), rawSpaceId);
        SpaceCategoryAnalyzeRequest categoryRequest =
                scoped(new SpaceCategoryAnalyzeRequest(), rawSpaceId);
        SpaceTagAnalyzeRequest tagRequest = scoped(new SpaceTagAnalyzeRequest(), rawSpaceId);
        SpaceSizeAnalyzeRequest sizeRequest = scoped(new SpaceSizeAnalyzeRequest(), rawSpaceId);
        SpaceUserAnalyzeRequest trendRequest = scoped(new SpaceUserAnalyzeRequest(), rawSpaceId);
        trendRequest.setTimeDimension("month");

        List<SpaceCategoryAnalyzeResponse> categories =
                boundedCategories(analyze.getSpaceCategoryAnalyze(categoryRequest, user));
        List<SpaceTagAnalyzeResponse> tags =
                head(analyze.getSpaceTagAnalyze(tagRequest, user), DISTRIBUTION_LIMIT);
        List<SpaceSizeAnalyzeResponse> sizes =
                head(analyze.getSpaceSizeAnalyze(sizeRequest, user), DISTRIBUTION_LIMIT);
        List<SpaceUserAnalyzeResponse> trend =
                tail(analyze.getSpaceUserAnalyze(trendRequest, user), TREND_LIMIT);

        Map<String, Object> scope = new LinkedHashMap<>();
        scope.put("type", rawSpaceId == null ? "public" : "space");
        scope.put("spaceId", rawSpaceId == null ? null : rawSpaceId.toString());

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("scope", scope);
        result.put("capturedAt", Instant.now(clock).toString());
        result.put("usage", analyze.getSpaceUsageAnalyze(usageRequest, user));
        result.put("categoryDistribution", categories);
        result.put("tagDistribution", tags);
        result.put("sizeDistribution", sizes);
        result.put("monthlyUploadTrend", trend);
        result.put("distributionLimit", DISTRIBUTION_LIMIT);
        result.put("trendLimit", TREND_LIMIT);
        Long spaceId = rawSpaceId == null ? null : Long.valueOf(rawSpaceId.toString());
        Map<String,Object> metrics = new LinkedHashMap<>();
        Map<String,Object> metadata = governance.metadata(spaceId,
                Date.from(Instant.now(clock).minus(java.time.Duration.ofDays(180))));
        Map<String,Object> features = governance.features(spaceId);
        if (metadata != null) metrics.putAll(metadata);
        if (features != null) metrics.putAll(features);
        result.put("governance", metrics);
        AgentStatisticsWindow filter=AgentStatisticsWindow.parse(
                (String)context.get("query"), java.time.LocalDate.now(clock.withZone(java.time.ZoneId.of("Asia/Shanghai"))));
        if(filter.active()) {
            Map<String,Object> window=new LinkedHashMap<>();
            window.put("startDate",filter.startDate); window.put("endDate",filter.endDate);
            window.put("uploaderId",filter.uploaderId==null?null:filter.uploaderId.toString());
            window.put("totals",windows.totals(spaceId,filter.start,filter.end,filter.uploaderId));
            window.put("categories",windows.categories(spaceId,filter.start,filter.end,filter.uploaderId));
            window.put("uploaders",windows.uploaders(spaceId,filter.start,filter.end,filter.uploaderId));
            window.put("tagDistribution",windows.tags(spaceId,filter.start,filter.end,filter.uploaderId));
            window.put("sizeDistribution",windows.sizes(spaceId,filter.start,filter.end,filter.uploaderId));
            window.put("governance",windows.governance(spaceId,filter.start,filter.end,filter.uploaderId,
                    Date.from(Instant.now(clock).minus(java.time.Duration.ofDays(180)))));
            List<Map<String,Object>> trendRows=windows.trend(spaceId,filter.start,filter.end,filter.uploaderId);
            Collections.reverse(trendRows);
            window.put("trend",trendRows);
            result.put("window",window);
        }
        return result;
    }

    private List<SpaceCategoryAnalyzeResponse> boundedCategories(
            List<SpaceCategoryAnalyzeResponse> values) {
        List<SpaceCategoryAnalyzeResponse> sorted =
                new ArrayList<>(values == null ? Collections.emptyList() : values);
        sorted.sort((left, right) -> Long.compare(count(right.getCount()), count(left.getCount())));
        return head(sorted, DISTRIBUTION_LIMIT);
    }

    private long count(Long value) {
        return value == null ? 0L : value;
    }

    private <T extends SpaceAnalyzeRequest> T scoped(T request, Object rawSpaceId) {
        if (rawSpaceId == null) {
            request.setQueryPublic(true);
        } else {
            request.setSpaceId(Long.valueOf(rawSpaceId.toString()));
        }
        return request;
    }

    private <T> List<T> head(List<T> values, int limit) {
        if (values == null || values.isEmpty()) return Collections.emptyList();
        return new ArrayList<>(values.subList(0, Math.min(values.size(), limit)));
    }

    private <T> List<T> tail(List<T> values, int limit) {
        if (values == null || values.isEmpty()) return Collections.emptyList();
        int from = Math.max(0, values.size() - limit);
        return new ArrayList<>(values.subList(from, values.size()));
    }
}
