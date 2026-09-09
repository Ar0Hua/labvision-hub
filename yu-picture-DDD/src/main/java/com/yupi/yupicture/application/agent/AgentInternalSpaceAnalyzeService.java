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
    private Clock clock = Clock.systemUTC();

    public Map<String, Object> summary(String bearerToken, String taskId) {
        Map<String, Object> context = internalTasks.context(bearerToken, taskId);
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
