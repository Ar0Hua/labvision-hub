package com.yupi.yupicture.application.agent;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.yupi.yupicture.domain.picture.entity.Picture;
import com.yupi.yupicture.domain.picture.repository.PictureRepository;
import com.yupi.yupicture.infrastructure.exception.BusinessException;
import com.yupi.yupicture.infrastructure.exception.ErrorCode;
import com.yupi.yupicture.interfaces.dto.agent.AgentInternalSearchRequest;
import org.springframework.stereotype.Service;

import javax.annotation.Resource;
import java.util.*;
import java.time.DateTimeException;
import java.time.LocalDate;

/** Agent 的关键词召回入口；空间范围只取自已签名且重新校验的任务上下文。 */
@Service
public class AgentInternalPictureSearchService {
    @Resource private AgentInternalTaskService internalTasks;
    @Resource private PictureRepository pictures;

    public List<Map<String, Object>> search(String bearerToken, String taskId, AgentInternalSearchRequest request) {
        Map<String, Object> context = internalTasks.context(bearerToken, taskId);
        validate(request);
        int limit = request.getLimit() == null ? 20 : request.getLimit();
        QueryWrapper<Picture> query = new QueryWrapper<>();
        query.select("id", "spaceId", "name", "introduction", "category", "tags",
                        "picSize", "picWidth", "picHeight", "picFormat", "createTime", "updateTime")
                .eq("isDelete", 0);
        Object spaceId = context.get("spaceId");
        if (spaceId == null) {
            query.isNull("spaceId").eq("reviewStatus", 1);
        } else {
            query.eq("spaceId", Long.valueOf(spaceId.toString()));
        }
        String text = trim(request.getSearchText());
        if (text != null) {
            query.and(wrapper -> wrapper.like("name", text)
                    .or().like("introduction", text)
                    .or().like("category", text)
                    .or().like("tags", text));
        }
        String category = trim(request.getCategory());
        if (category != null) query.eq("category", category);
        if (request.getTags() != null) {
            for (String tag : new LinkedHashSet<>(request.getTags())) {
                query.like("tags", "\"" + tag.trim() + "\"");
            }
        }
        if (request.getFormats() != null && !request.getFormats().isEmpty()) {
            Set<String> formats = new LinkedHashSet<>();
            for (String format : request.getFormats()) formats.add(format.trim().toLowerCase(Locale.ROOT));
            query.in("picFormat", formats);
        }
        LocalDate after = date(request.getCreatedAfter());
        LocalDate before = date(request.getCreatedBefore());
        if (after != null) query.ge("createTime", after.atStartOfDay());
        if (before != null) query.lt("createTime", before.plusDays(1).atStartOfDay());
        if (request.getMinWidth() != null) query.ge("picWidth", request.getMinWidth());
        if (request.getMinHeight() != null) query.ge("picHeight", request.getMinHeight());
        if (request.getMaxSizeBytes() != null)
            query.le("picSize", request.getMaxSizeBytes());
        String sort = trim(request.getSort());
        if ("oldest".equals(sort)) {
            query.orderByAsc("createTime").orderByAsc("id");
        } else {
            query.orderByDesc("createTime").orderByDesc("id");
        }
        query.last("LIMIT " + limit);
        List<Map<String, Object>> result = new ArrayList<>();
        for (Picture picture : pictures.list(query)) {
            Map<String, Object> item = new LinkedHashMap<>();
            item.put("pictureId", picture.getId().toString());
            item.put("spaceId", picture.getSpaceId() == null ? null : picture.getSpaceId().toString());
            item.put("name", picture.getName());
            item.put("introduction", picture.getIntroduction());
            item.put("category", picture.getCategory());
            item.put("tags", picture.getTags());
            item.put("width", picture.getPicWidth());
            item.put("height", picture.getPicHeight());
            item.put("size", picture.getPicSize());
            item.put("format", picture.getPicFormat());
            item.put("createdAt", picture.getCreateTime());
            result.add(item);
        }
        return result;
    }

    private void validate(AgentInternalSearchRequest request) {
        if (request == null || request.getLimit() != null && (request.getLimit() < 1 || request.getLimit() > 20)) {
            invalid();
        }
        check(trim(request.getSearchText()), 100);
        check(trim(request.getCategory()), 32);
        if (request.getTags() != null) {
            if (request.getTags().size() > 5) invalid();
            for (String tag : request.getTags()) {
                if (tag == null || tag.trim().isEmpty()) invalid();
                check(tag.trim(), 32);
            }
        }
        if (request.getFormats() != null) {
            if (request.getFormats().size() > 5) invalid();
            Set<String> allowed = new HashSet<>(Arrays.asList(
                    "jpg", "jpeg", "png", "webp", "gif", "bmp", "tif", "tiff"));
            for (String format : request.getFormats())
                if (format == null || !allowed.contains(format.trim().toLowerCase(Locale.ROOT))) invalid();
        }
        if (request.getMinWidth() != null && (request.getMinWidth() < 1 || request.getMinWidth() > 100000)) invalid();
        if (request.getMinHeight() != null && (request.getMinHeight() < 1 || request.getMinHeight() > 100000)) invalid();
        if (request.getMaxSizeBytes() != null
                && (request.getMaxSizeBytes() < 1 || request.getMaxSizeBytes() > 10737418240L)) invalid();
        LocalDate after = date(request.getCreatedAfter());
        LocalDate before = date(request.getCreatedBefore());
        if (after != null && before != null && after.isAfter(before)) invalid();
        String sort = trim(request.getSort());
        if (sort != null && !Arrays.asList("relevance", "newest", "oldest").contains(sort)) invalid();
    }

    private String trim(String value) {
        if (value == null || value.trim().isEmpty()) return null;
        return value.trim();
    }
    private void check(String value, int max) { if (value != null && value.length() > max) invalid(); }
    private LocalDate date(String value) {
        String normalized = trim(value);
        if (normalized == null) return null;
        try {
            LocalDate result = LocalDate.parse(normalized);
            if (result.getYear() < 1970 || result.getYear() > 2100) invalid();
            return result;
        } catch (DateTimeException exception) {
            invalid();
            return null;
        }
    }
    private void invalid() { throw new BusinessException(ErrorCode.PARAMS_ERROR, "非法图片检索条件"); }
}
