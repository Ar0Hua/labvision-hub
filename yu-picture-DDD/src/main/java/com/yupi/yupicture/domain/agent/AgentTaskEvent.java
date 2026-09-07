package com.yupi.yupicture.domain.agent;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import java.util.Date;

@Data
@TableName("agent_task_event")
public class AgentTaskEvent {
    @TableId(type = IdType.AUTO)
    private Long id;
    private String taskId;
    private String eventType;
    private String payloadJson;
    private Date createTime;
}
