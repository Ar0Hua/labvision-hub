package com.yupi.yupicture.application.agent;

import com.yupi.yupicture.domain.agent.AgentMessage;
import com.yupi.yupicture.domain.agent.AgentTask;
import com.yupi.yupicture.domain.user.entity.User;
import com.yupi.yupicture.infrastructure.exception.BusinessException;
import com.yupi.yupicture.infrastructure.exception.ErrorCode;
import com.yupi.yupicture.infrastructure.mapper.AgentTaskMapper;
import com.yupi.yupicture.interfaces.vo.agent.AgentTaskVO;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import javax.annotation.Resource;
import java.util.UUID;

@Service
public class AgentTaskService {
    @Resource private AgentConversationService conversations;
    @Resource private AgentMessageService messages;
    @Resource private AgentTaskMapper mapper;

    /** 消息和任务必须同时成功或同时回滚。 */
    @Transactional(rollbackFor = Exception.class)
    public AgentTaskVO submit(String conversationId, String content, User user) {
        AgentMessage message = messages.createUserMessage(conversationId, content, user);
        AgentTask task = new AgentTask();
        task.setId(UUID.randomUUID().toString());
        task.setConversationId(conversationId);
        task.setInputMessageId(message.getId());
        task.setUserId(user.getId());
        task.setStatus("PENDING");
        task.setStage("QUEUED");
        if (mapper.insert(task) != 1) {
            throw new BusinessException(ErrorCode.OPERATION_ERROR, "任务创建失败");
        }
        return AgentTaskVO.from(task);
    }

    public AgentTaskVO get(String taskId, User user) {
        if (taskId == null || !taskId.matches("[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")) {
            deny();
        }
        AgentTask task = mapper.selectById(taskId);
        if (task == null) {
            deny();
        }
        conversations.requireOwner(task.getConversationId(), user);
        return AgentTaskVO.from(task);
    }

    private void deny() {
        throw new BusinessException(ErrorCode.NO_AUTH_ERROR, "任务不可访问");
    }
}
