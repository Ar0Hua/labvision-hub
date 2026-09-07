package com.yupi.yupicture.application.agent;

import lombok.Data;

@Data
public class AgentWorkerContext {
    private String purpose;
    private String nonce;
    private long issuedAt;
    private long expiresAt;
}
