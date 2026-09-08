package com.yupi.yupicture.application.agent;

import cn.hutool.core.util.StrUtil;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.UpdateWrapper;
import com.yupi.yupicture.domain.agent.AgentPictureIndexOutbox;
import com.yupi.yupicture.domain.picture.entity.Picture;
import com.yupi.yupicture.domain.picture.repository.PictureRepository;
import com.yupi.yupicture.infrastructure.api.CosManager;
import com.yupi.yupicture.infrastructure.exception.*;
import com.yupi.yupicture.infrastructure.mapper.AgentPictureIndexOutboxMapper;
import com.yupi.yupicture.interfaces.dto.agent.AgentIndexAckRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import javax.annotation.Resource;
import java.time.Instant;
import java.util.*;

@Service
public class AgentPictureIndexJobService {
    private static final long LEASE_SECONDS = 300L;
    private static final int INDEX_URL_TTL_SECONDS = 300;
    @Resource private AgentServiceTokenService tokens;
    @Resource private AgentPictureIndexOutboxMapper jobs;
    @Resource private AgentPictureFeatureService features;
    @Resource private PictureRepository pictures;
    @Resource private CosManager cos;

    @Transactional(rollbackFor = Exception.class)
    public List<Map<String,Object>> claim(String authorization, Integer requestedLimit) {
        authenticate(authorization);
        int limit = requestedLimit == null ? 10 : requestedLimit;
        if (limit < 1 || limit > 20) invalid();
        Date now = new Date();
        Date expired = Date.from(Instant.ofEpochMilli(now.getTime()).minusSeconds(LEASE_SECONDS));
        List<AgentPictureIndexOutbox> rows = jobs.selectList(new QueryWrapper<AgentPictureIndexOutbox>()
                .and(w -> w.and(x -> x.in("status", "PENDING", "FAILED").le("availableAt", now))
                        .or(x -> x.eq("status", "PROCESSING").lt("lockedAt", expired)))
                .orderByAsc("id").last("LIMIT " + limit + " FOR UPDATE SKIP LOCKED"));
        List<Map<String,Object>> result = new ArrayList<>();
        for (AgentPictureIndexOutbox row : rows) {
            String lease = UUID.randomUUID().toString();
            row.setStatus("PROCESSING");
            row.setLockedAt(now);
            row.setLeaseToken(lease);
            row.setAttemptCount((row.getAttemptCount() == null ? 0 : row.getAttemptCount()) + 1);
            row.setLastError(null);
            if (jobs.updateById(row) != 1) {
                throw new BusinessException(ErrorCode.OPERATION_ERROR, "索引任务领取失败");
            }
            result.add(snapshot(row, lease));
        }
        return result;
    }

    @Transactional(rollbackFor = Exception.class)
    public void acknowledge(String authorization, Long jobId, AgentIndexAckRequest request) {
        authenticate(authorization);
        if (jobId == null || jobId < 1 || request == null || request.getSuccess() == null
                || request.getLeaseToken() == null
                || !request.getLeaseToken().matches("[0-9a-f-]{36}")) invalid();
        AgentPictureIndexOutbox row = jobs.selectById(jobId);
        if (row == null || !"PROCESSING".equals(row.getStatus())
                || !request.getLeaseToken().equals(row.getLeaseToken())) {
            throw new BusinessException(ErrorCode.OPERATION_ERROR, "索引任务租约已失效");
        }
        UpdateWrapper<AgentPictureIndexOutbox> update = new UpdateWrapper<AgentPictureIndexOutbox>()
                .eq("id", jobId).eq("status", "PROCESSING").eq("leaseToken", request.getLeaseToken())
                .set("lockedAt", null).set("leaseToken", null);
        if (request.getSuccess()) {
            update.set("status", "PROCESSED").set("lastError", null);
            if (Boolean.TRUE.equals(request.getDeleted())) {
                features.deleted(row.getPictureId());
            } else {
                features.ready(row.getPictureId(), request);
            }
        } else {
            int attempts = row.getAttemptCount() == null ? 1 : row.getAttemptCount();
            long delay = Math.min(300L, 5L * (1L << Math.min(attempts - 1, 6)));
            update.set("status", "FAILED")
                    .set("availableAt", Date.from(Instant.now().plusSeconds(delay)))
                    .set("lastError", safeError(request.getErrorMessage()));
            features.failed(row.getPictureId(), request.getErrorMessage());
        }
        if (jobs.update(null, update) != 1) {
            throw new BusinessException(ErrorCode.OPERATION_ERROR, "索引任务确认失败");
        }
    }

    private Map<String,Object> snapshot(AgentPictureIndexOutbox row, String lease) {
        Picture picture = pictures.getById(row.getPictureId());
        boolean delete = picture == null || Integer.valueOf(1).equals(picture.getIsDelete())
                || picture.getSpaceId() == null && !Integer.valueOf(1).equals(picture.getReviewStatus());
        Map<String,Object> item = new LinkedHashMap<>();
        item.put("jobId", row.getId().toString());
        item.put("leaseToken", lease);
        item.put("pictureId", row.getPictureId().toString());
        item.put("operation", delete ? "DELETE" : "UPSERT");
        if (!delete) {
            item.put("scopeKey", picture.getSpaceId() == null ? "public" : "space:" + picture.getSpaceId());
            item.put("spaceId", picture.getSpaceId() == null ? null : picture.getSpaceId().toString());
            item.put("userId", picture.getUserId() == null ? null : picture.getUserId().toString());
            item.put("reviewStatus", picture.getReviewStatus());
            item.put("name", picture.getName());
            item.put("introduction", picture.getIntroduction());
            item.put("category", picture.getCategory());
            item.put("tags", picture.getTags());
            item.put("picFormat", picture.getPicFormat());
            item.put("picWidth", picture.getPicWidth());
            item.put("picHeight", picture.getPicHeight());
            item.put("picSize", picture.getPicSize());
            item.put("picColor", picture.getPicColor());
            item.put("createdAtEpoch", epochSeconds(picture.getCreateTime()));
            item.put("sourceUpdatedAtEpoch", epochSeconds(sourceUpdatedAt(picture)));
            String source = StrUtil.isNotBlank(picture.getThumbnailUrl())
                    ? picture.getThumbnailUrl() : picture.getUrl();
            if (StrUtil.isBlank(source)) {
                throw new BusinessException(ErrorCode.OPERATION_ERROR, "索引图片没有可用对象地址");
            }
            try {
                item.put("temporaryUrl", cos.generatePresignedGetUrl(source, INDEX_URL_TTL_SECONDS));
            } catch (IllegalArgumentException exception) {
                throw new BusinessException(ErrorCode.OPERATION_ERROR, "索引图片临时地址生成失败");
            }
        }
        return item;
    }

    private Date sourceUpdatedAt(Picture picture) {
        if (picture.getUpdateTime() != null) return picture.getUpdateTime();
        if (picture.getEditTime() != null) return picture.getEditTime();
        return picture.getCreateTime();
    }

    private Long epochSeconds(Date value) {
        return value == null ? null : value.getTime() / 1000L;
    }
    private void authenticate(String authorization) {
        if (authorization == null || !authorization.startsWith("Bearer ")) {
            throw new BusinessException(ErrorCode.NO_AUTH_ERROR, "索引 Worker 令牌无效");
        }
        tokens.verifyWorker(authorization.substring(7));
    }
    private String safeError(String value) {
        if (value == null || value.trim().isEmpty()) return "INDEX_WORKER_ERROR";
        String cleaned = value.replaceAll("[\\r\\n\\t]", " ").trim();
        return cleaned.length() <= 256 ? cleaned : cleaned.substring(0, 256);
    }
    private void invalid() { throw new BusinessException(ErrorCode.PARAMS_ERROR, "非法索引任务请求"); }
}
