package com.yupi.yupicture.domain.agent;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;
import java.util.Date;

@Data
@TableName("agent_task")
public class AgentTask {
    @TableId(type = IdType.INPUT)
    private String id;
    private String conversationId;
    private String inputMessageId;
    private Long userId;
    private String status;
    private String stage;
    private String errorCode;
    private String errorMessage;
    private Integer retryCount;
    private Date createTime;
    private Date updateTime;
}
