package com.yupi.yupicture.application.agent;

import cn.hutool.json.JSONUtil;
import com.yupi.yupicture.infrastructure.exception.*;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.security.*;
import java.time.*;
import java.util.*;

@Service
public class AgentServiceTokenService {
    private static final long TTL_SECONDS = 300L;
    @Value("${agent.internal.secret:${AGENT_INTERNAL_SECRET:}}")
    private String secret;
    private Clock clock = Clock.systemUTC();

    public String issue(String taskId, String conversationId, Long userId, Long spaceId) {
        requireSecret();
        AgentServiceContext context = new AgentServiceContext();
        context.setTaskId(taskId);
        context.setConversationId(conversationId);
        context.setUserId(userId.toString());
        context.setSpaceId(spaceId == null ? null : spaceId.toString());
        context.setIssuedAt(Instant.now(clock).getEpochSecond());
        context.setExpiresAt(context.getIssuedAt() + TTL_SECONDS);
        String payload = encode(JSONUtil.toJsonStr(context).getBytes(StandardCharsets.UTF_8));
        return payload + "." + encode(sign(payload));
    }

    public AgentServiceContext verify(String token, String expectedTaskId) {
        requireSecret();
        if (token == null || expectedTaskId == null) deny();
        String[] parts = token.split("\\.", -1);
        if (parts.length != 2) deny();
        byte[] supplied;
        try {
            supplied = Base64.getUrlDecoder().decode(parts[1]);
        } catch (IllegalArgumentException error) {
            deny(); return null;
        }
        if (!MessageDigest.isEqual(sign(parts[0]), supplied)) deny();
        try {
            AgentServiceContext context = JSONUtil.toBean(
                    new String(Base64.getUrlDecoder().decode(parts[0]), StandardCharsets.UTF_8),
                    AgentServiceContext.class);
            long now = Instant.now(clock).getEpochSecond();
            if (!expectedTaskId.equals(context.getTaskId()) || context.getExpiresAt() < now
                    || context.getIssuedAt() > now + 30 || context.getExpiresAt() - context.getIssuedAt() != TTL_SECONDS) {
                deny();
            }
            return context;
        } catch (RuntimeException error) {
            deny(); return null;
        }
    }

    private byte[] sign(String payload) {
        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(secret.getBytes(StandardCharsets.UTF_8), "HmacSHA256"));
            return mac.doFinal(payload.getBytes(StandardCharsets.UTF_8));
        } catch (GeneralSecurityException error) {
            throw new BusinessException(ErrorCode.SYSTEM_ERROR, "Agent 服务签名失败");
        }
    }

    private String encode(byte[] value) {
        return Base64.getUrlEncoder().withoutPadding().encodeToString(value);
    }

    private void requireSecret() {
        if (secret == null || secret.length() < 32) {
            throw new BusinessException(ErrorCode.SYSTEM_ERROR, "Agent 内部密钥未配置或长度不足");
        }
    }

    private void deny() {
        throw new BusinessException(ErrorCode.NO_AUTH_ERROR, "Agent 服务令牌无效或已过期");
    }
}
