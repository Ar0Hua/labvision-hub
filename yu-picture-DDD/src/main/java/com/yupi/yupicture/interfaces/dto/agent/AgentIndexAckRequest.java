package com.yupi.yupicture.interfaces.dto.agent;

import lombok.Data;

@Data
public class AgentIndexAckRequest {
    private String leaseToken;
    private Boolean success;
    private String errorMessage;
}
