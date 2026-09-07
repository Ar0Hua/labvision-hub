package com.yupi.yupicture.interfaces.dto.agent;
import lombok.Data;
@Data
public class AgentInternalStateRequest {
    private String status;
    private String stage;
    private String errorCode;
    private String errorMessage;
}
