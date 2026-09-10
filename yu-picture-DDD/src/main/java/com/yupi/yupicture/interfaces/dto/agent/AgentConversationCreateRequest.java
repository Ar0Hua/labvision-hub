package com.yupi.yupicture.interfaces.dto.agent;
import lombok.Data;
/** 空间为空时仅访问公共图库。 */
@Data
public class AgentConversationCreateRequest {
 private Long spaceId;
 private Boolean allSpaces;
}
