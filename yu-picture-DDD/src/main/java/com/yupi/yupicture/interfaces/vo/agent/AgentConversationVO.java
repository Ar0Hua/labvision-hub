package com.yupi.yupicture.interfaces.vo.agent;

import com.yupi.yupicture.domain.agent.AgentConversation;
import lombok.Data;
import java.util.Date;

@Data
public class AgentConversationVO {
    private String conversationId;
    private String spaceId;
    private String status;
    private Date createTime;
    private Date updateTime;

    public static AgentConversationVO from(AgentConversation row) {
        AgentConversationVO vo = new AgentConversationVO();
        vo.setConversationId(row.getId());
        vo.setSpaceId(row.getSpaceId() == null ? null : row.getSpaceId().toString());
        vo.setStatus(row.getStatus());
        vo.setCreateTime(row.getCreateTime());
        vo.setUpdateTime(row.getUpdateTime());
        return vo;
    }
}
