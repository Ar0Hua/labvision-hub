package com.yupi.yupicture.domain.agent;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.util.Date;

@Data
@TableName("picture_ai_feature")
public class PictureAiFeature {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long pictureId;
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
    private String indexStatus;
    private Date lastIndexedAt;
    private String lastError;
    private Date sourceUpdatedAt;
    private Date createTime;
    private Date updateTime;
}
