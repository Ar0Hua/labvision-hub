package com.yupi.yupicture.application.agent;

import com.yupi.yupicture.domain.agent.AgentConversation;
import com.yupi.yupicture.domain.agent.AgentTask;
import com.yupi.yupicture.infrastructure.exception.BusinessException;
import com.yupi.yupicture.infrastructure.exception.ErrorCode;
import com.yupi.yupicture.infrastructure.mapper.AgentConversationMapper;
import com.yupi.yupicture.infrastructure.mapper.AgentTaskMapper;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import javax.annotation.Resource;
import java.net.URI;
import java.util.Objects;

@Service
public class AgentTaskDispatchGateway {
    @Resource private AgentTaskMapper tasks;
    @Resource private AgentConversationMapper conversations;
    @Resource private AgentServiceTokenService tokens;
    @Resource @Qualifier("agentRestTemplate") private RestTemplate client;
    @Value("${agent.service.base-url:http://127.0.0.1:8000}") private String baseUrl;

    /** 只分发仍处于排队状态的任务，避免取消与异步提交发生竞争。 */
    public void dispatch(String taskId) {
        AgentTask task = tasks.selectById(taskId);
        if (task == null || !"PENDING".equals(task.getStatus())) {
            return;
        }
        AgentConversation conversation = conversations.selectById(task.getConversationId());
        if (conversation == null || !"ACTIVE".equals(conversation.getStatus())
                || !Objects.equals(task.getUserId(), conversation.getUserId())) {
            throw new BusinessException(ErrorCode.OPERATION_ERROR, "Agent 任务上下文已失效");
        }
        String token = tokens.issue(taskId, task.getConversationId(), task.getUserId(), conversation.getSpaceId());
        HttpHeaders headers = new HttpHeaders();
        headers.setBearerAuth(token);
        client.exchange(endpoint(taskId), HttpMethod.POST, new HttpEntity<Void>(headers), Void.class);
    }

    private URI endpoint(String taskId) {
        URI base;
        try {
            base = URI.create(baseUrl);
        } catch (IllegalArgumentException error) {
            throw new BusinessException(ErrorCode.SYSTEM_ERROR, "Agent 服务地址配置无效");
        }
        if (base.getHost() == null || base.getUserInfo() != null
                || !("http".equalsIgnoreCase(base.getScheme()) || "https".equalsIgnoreCase(base.getScheme()))) {
            throw new BusinessException(ErrorCode.SYSTEM_ERROR, "Agent 服务地址配置无效");
        }
        String normalized = baseUrl.endsWith("/") ? baseUrl.substring(0, baseUrl.length() - 1) : baseUrl;
        return URI.create(normalized + "/internal/tasks/" + taskId + "/run");
    }
}
