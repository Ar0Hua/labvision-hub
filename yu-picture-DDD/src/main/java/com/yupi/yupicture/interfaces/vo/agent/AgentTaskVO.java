package com.yupi.yupicture.interfaces.vo.agent;

import com.yupi.yupicture.domain.agent.AgentTask;
import lombok.Data;

@Data
public class AgentTaskVO {
    private String taskId;
    private String conversationId;
    private String inputMessageId;
    private String status;
    private String stage;
    private String errorCode;
    private String errorMessage;

    public static AgentTaskVO from(AgentTask task) {
        AgentTaskVO vo = new AgentTaskVO();
        vo.setTaskId(task.getId());
        vo.setConversationId(task.getConversationId());
        vo.setInputMessageId(task.getInputMessageId());
        vo.setStatus(task.getStatus());
        vo.setStage(task.getStage());
        vo.setErrorCode(task.getErrorCode());
        vo.setErrorMessage(task.getErrorMessage());
        return vo;
    }
}
