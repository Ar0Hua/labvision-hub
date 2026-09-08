package com.yupi.yupicture.interfaces.dto.agent;

import lombok.Data;

@Data
public class AgentIndexAckRequest {
    private String leaseToken;
    private Boolean success;
    private Boolean deleted;
    private String errorMessage;
    private String caption;
    private String ocrText;
    private String contentHash;
    private String phash;
    private String dhash;
    private Double blurScore;
    private Double brightnessScore;
    private String qualityFlags;
    private String embeddingModel;
    private String embeddingVersion;
    private String captionModel;
    private String promptVersion;
    private Long sourceUpdatedAtEpoch;
}
