package com.yupi.yupicture.interfaces.vo.agent;

import com.yupi.yupicture.domain.agent.AgentTask;
import lombok.Data;
import java.util.Date;

@Data
public class AgentTaskVO {
    private String taskId;
    private String conversationId;
    private String inputMessageId;
    private String status;
    private String stage;
    private String errorCode;
    private String errorMessage;
    private Integer retryCount;
    private Date createTime;
    private Date updateTime;

    public static AgentTaskVO from(AgentTask task) {
        AgentTaskVO vo = new AgentTaskVO();
        vo.setTaskId(task.getId());
        vo.setConversationId(task.getConversationId());
        vo.setInputMessageId(task.getInputMessageId());
        vo.setStatus(task.getStatus());
        vo.setStage(task.getStage());
        vo.setErrorCode(task.getErrorCode());
        vo.setErrorMessage(task.getErrorMessage());
        vo.setRetryCount(task.getRetryCount());
        vo.setCreateTime(task.getCreateTime());
        vo.setUpdateTime(task.getUpdateTime());
        return vo;
    }
}
