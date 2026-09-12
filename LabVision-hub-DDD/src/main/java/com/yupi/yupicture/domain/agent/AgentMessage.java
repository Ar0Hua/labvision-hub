package com.yupi.yupicture.domain.agent;
import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import java.util.Date;
@Data @TableName("agent_message")
public class AgentMessage {
 @TableId(type = IdType.INPUT) private String id;
 private String conversationId;
 private Long userId;
 private String role;
 private String content;
 private Date createTime;
}
