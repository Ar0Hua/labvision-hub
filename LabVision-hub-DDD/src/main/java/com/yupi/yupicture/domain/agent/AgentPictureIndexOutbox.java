package com.yupi.yupicture.domain.agent;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.util.Date;

@Data
@TableName("agent_picture_index_outbox")
public class AgentPictureIndexOutbox {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long pictureId;
    private String operation;
    private String status;
    private Integer attemptCount;
    private Date availableAt;
    private Date lockedAt;
    private String leaseToken;
    private String lastError;
    private String dedupeKey;
    private Date createTime;
    private Date updateTime;
}
