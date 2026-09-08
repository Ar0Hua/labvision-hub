package com.yupi.yupicture.application.agent;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.yupi.yupicture.domain.agent.PictureAiFeature;
import com.yupi.yupicture.infrastructure.mapper.PictureAiFeatureMapper;
import com.yupi.yupicture.interfaces.dto.agent.AgentIndexAckRequest;
import org.springframework.stereotype.Service;

import javax.annotation.Resource;
import java.util.Date;

@Service
public class AgentPictureFeatureService {
    @Resource private PictureAiFeatureMapper features;

    public void ready(Long pictureId, AgentIndexAckRequest request) {
        PictureAiFeature feature = find(pictureId);
        if (feature == null) {
            feature = new PictureAiFeature();
            feature.setPictureId(pictureId);
        }
        feature.setCaption(trim(request.getCaption(), 2000));
        feature.setOcrText(trim(request.getOcrText(), 4000));
        feature.setContentHash(trim(request.getContentHash(), 64));
        feature.setPhash(trim(request.getPhash(), 16));
        feature.setDhash(trim(request.getDhash(), 16));
        feature.setBlurScore(request.getBlurScore());
        feature.setBrightnessScore(request.getBrightnessScore());
        feature.setQualityFlags(trim(request.getQualityFlags(), 512));
        feature.setEmbeddingModel(trim(request.getEmbeddingModel(), 128));
        feature.setEmbeddingVersion(trim(request.getEmbeddingVersion(), 64));
        feature.setCaptionModel(trim(request.getCaptionModel(), 128));
        feature.setPromptVersion(trim(request.getPromptVersion(), 64));
        feature.setIndexStatus("READY");
        feature.setLastIndexedAt(new Date());
        feature.setLastError(null);
        if (request.getSourceUpdatedAtEpoch() != null && request.getSourceUpdatedAtEpoch() > 0) {
            feature.setSourceUpdatedAt(new Date(request.getSourceUpdatedAtEpoch() * 1000L));
        }
        save(feature);
    }

    public void deleted(Long pictureId) {
        features.delete(new QueryWrapper<PictureAiFeature>().eq("pictureId", pictureId));
    }

    public void failed(Long pictureId, String error) {
        PictureAiFeature feature = find(pictureId);
        if (feature == null) {
            feature = new PictureAiFeature();
            feature.setPictureId(pictureId);
        }
        feature.setIndexStatus("FAILED");
        feature.setLastError(trim(error == null ? "INDEX_WORKER_ERROR" : error, 512));
        save(feature);
    }

    private PictureAiFeature find(Long pictureId) {
        return features.selectOne(new QueryWrapper<PictureAiFeature>()
                .eq("pictureId", pictureId).last("LIMIT 1"));
    }

    private void save(PictureAiFeature feature) {
        if (feature.getId() == null) features.insert(feature); else features.updateById(feature);
    }

    private String trim(String value, int max) {
        if (value == null) return null;
        String cleaned = value.replace("\u0000", "").trim();
        return cleaned.length() <= max ? cleaned : cleaned.substring(0, max);
    }
}
