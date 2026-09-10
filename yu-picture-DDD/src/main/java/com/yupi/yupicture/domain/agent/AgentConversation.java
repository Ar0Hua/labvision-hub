package com.yupi.yupicture.domain.agent;
import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import java.util.Date;
@Data
@TableName("agent_conversation")
public class AgentConversation {
 @TableId(type = IdType.INPUT)
 private String id;
 private Long userId;
 private String status;
 private Long spaceId;
 private Boolean allSpaces;
 private String scopeSpaceIdsJson;
 private Date createTime;
 private Date updateTime;
}
