package com.yupi.yupicture.domain.agent;
import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
@Data
@TableName("agent_conversation")
public class AgentConversation {
 @TableId(type = IdType.INPUT)
 private String id;
 private Long userId;
 private String status;
}
