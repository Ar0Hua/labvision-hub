package com.yupi.yupicture.application.agent;

import com.yupi.yupicture.domain.user.entity.User;
import org.springframework.stereotype.Service;

import javax.annotation.Resource;
import java.util.List;
import java.util.Map;
import java.util.*;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.yupi.yupicture.domain.agent.PictureAiFeature;
import com.yupi.yupicture.domain.picture.entity.Picture;
import com.yupi.yupicture.domain.picture.repository.PictureRepository;
import com.yupi.yupicture.infrastructure.mapper.PictureAiFeatureMapper;

/** 对外部索引返回的候选 ID 逐项回源鉴权，Qdrant payload 不能替代此检查。 */
@Service
public class AgentInternalPictureDetailsService {
    @Resource private AgentInternalTaskService internalTasks;
    @Resource private AgentPictureService pictures;
    @Resource private PictureAiFeatureMapper features;
    @Resource private PictureRepository sourcePictures;

    public List<Map<String, Object>> details(String bearerToken, String taskId, List<Long> pictureIds) {
        Map<String, Object> context = internalTasks.context(bearerToken, taskId);
        User user = new User();
        user.setId(Long.valueOf(context.get("userId").toString()));
        List<Map<String, Object>> authorized =
                pictures.details(context.get("conversationId").toString(), pictureIds, user);
        List<Map<String, Object>> result = new ArrayList<>();
        for (Map<String, Object> value : authorized) {
            Map<String, Object> item = new LinkedHashMap<>(value);
            Long id = Long.valueOf(value.get("pictureId").toString());
            Picture source = sourcePictures.getById(id);
            PictureAiFeature feature = features.selectOne(
                    new QueryWrapper<PictureAiFeature>().eq("pictureId", id).last("LIMIT 1"));
            Date version = source == null ? null : (source.getUpdateTime() != null
                    ? source.getUpdateTime() : (source.getEditTime() != null
                    ? source.getEditTime() : source.getCreateTime()));
            if (feature != null && "READY".equals(feature.getIndexStatus())
                    && version != null && feature.getSourceUpdatedAt() != null
                    && version.getTime() / 1000 == feature.getSourceUpdatedAt().getTime() / 1000) {
                Map<String, Object> evidence = new LinkedHashMap<>();
                evidence.put("contentHash", feature.getContentHash());
                evidence.put("phash", feature.getPhash());
                evidence.put("dhash", feature.getDhash());
                evidence.put("blurScore", feature.getBlurScore());
                evidence.put("brightnessScore", feature.getBrightnessScore());
                evidence.put("qualityFlags", feature.getQualityFlags());
                evidence.put("caption", feature.getCaption());
                evidence.put("ocrText", feature.getOcrText());
                evidence.put("indexedAt", feature.getLastIndexedAt() == null
                        ? null : feature.getLastIndexedAt().toInstant().toString());
                item.put("features", evidence);
            }
            result.add(item);
        }
        return result;
    }
}
