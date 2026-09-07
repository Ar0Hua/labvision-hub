package com.yupi.yupicture.interfaces.dto.agent;
import lombok.Data;
@Data
public class AgentInternalEventRequest {
    private String eventType;
    private String payloadJson;
}
