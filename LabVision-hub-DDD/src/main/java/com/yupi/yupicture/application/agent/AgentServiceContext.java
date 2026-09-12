package com.yupi.yupicture.application.agent;

import lombok.Data;

/** Java 签发给 Agent 服务的最小短期身份上下文。 */
@Data
public class AgentServiceContext {
    private String taskId;
    private String conversationId;
    private String userId;
    private String spaceId;
    private int attempt;
    private long issuedAt;
    private long expiresAt;
}
