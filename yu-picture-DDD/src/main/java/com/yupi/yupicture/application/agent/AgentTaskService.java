package com.yupi.yupicture.application.agent;

import com.yupi.yupicture.domain.agent.AgentMessage;
import com.yupi.yupicture.domain.agent.AgentTask;
import com.yupi.yupicture.domain.user.entity.User;
import com.yupi.yupicture.infrastructure.exception.BusinessException;
import com.yupi.yupicture.infrastructure.exception.ErrorCode;
import com.yupi.yupicture.infrastructure.mapper.AgentTaskMapper;
import com.yupi.yupicture.interfaces.vo.agent.AgentTaskVO;
import com.baomidou.mybatisplus.core.conditions.update.UpdateWrapper;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import org.springframework.stereotype.Service;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.transaction.annotation.Transactional;
import javax.annotation.Resource;
import java.util.UUID;
import java.util.List;
import java.util.stream.Collectors;

@Service
public class AgentTaskService {
    @Resource private AgentConversationService conversations;
    @Resource private AgentMessageService messages;
    @Resource private AgentTaskMapper mapper;
    @Resource private AgentTaskEventService events;
    @Resource private ApplicationEventPublisher publisher;

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
        task.setRetryCount(0);
        if (mapper.insert(task) != 1) {
            throw new BusinessException(ErrorCode.OPERATION_ERROR, "任务创建失败");
        }
        events.append(task.getId(), "status", "{\"stage\":\"queued\"}");
        publisher.publishEvent(new AgentTaskDispatchRequested(task.getId()));
        return AgentTaskVO.from(task);
    }

    public AgentTaskVO get(String taskId, User user) {
        return AgentTaskVO.from(requireTask(taskId, user));
    }

    public List<AgentTaskVO> listByConversation(String conversationId, User user) {
        conversations.requireOwner(conversationId, user);
        return mapper.selectList(new QueryWrapper<AgentTask>()
                        .eq("conversationId", conversationId)
                        .orderByAsc("createTime")
                        .orderByAsc("id")
                        .last("LIMIT 50"))
                .stream().map(AgentTaskVO::from).collect(Collectors.toList());
    }

    @Transactional(rollbackFor = Exception.class)
    public AgentTaskVO cancel(String taskId, User user) {
        AgentTask task = requireTask(taskId, user);
        if ("CANCELLED".equals(task.getStatus())) {
            return AgentTaskVO.from(task);
        }
        int changed = mapper.update(null, new UpdateWrapper<AgentTask>()
                .eq("id", taskId).in("status", "PENDING", "RUNNING")
                .set("status", "CANCELLED").set("stage", "CANCELLED"));
        if (changed != 1) {
            throw new BusinessException(ErrorCode.OPERATION_ERROR, "任务状态已变化，请刷新后重试");
        }
        events.append(taskId, "status", "{\"status\":\"CANCELLED\",\"stage\":\"CANCELLED\"}");
        return get(taskId, user);
    }

    @Transactional(rollbackFor = Exception.class)
    public AgentTaskVO resume(String taskId, User user) {
        AgentTask task = requireTask(taskId, user);
        int retries = task.getRetryCount() == null ? 0 : task.getRetryCount();
        int changed = mapper.update(null, new UpdateWrapper<AgentTask>()
                .eq("id", taskId).in("status", "FAILED", "CANCELLED")
                .set("status", "PENDING").set("stage", "QUEUED")
                .set("errorCode", null).set("errorMessage", null)
                .set("retryCount", retries + 1));
        if (changed != 1) {
            throw new BusinessException(ErrorCode.OPERATION_ERROR, "只有失败或已取消任务可以重试");
        }
        publisher.publishEvent(new AgentTaskDispatchRequested(taskId));
        return get(taskId, user);
    }

    private AgentTask requireTask(String taskId, User user) {
        if (taskId == null || !taskId.matches("[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")) {
            deny();
        }
        AgentTask task = mapper.selectById(taskId);
        if (task == null) {
            deny();
        }
        conversations.requireOwner(task.getConversationId(), user);
        return task;
    }

    private void deny() {
        throw new BusinessException(ErrorCode.NO_AUTH_ERROR, "任务不可访问");
    }
}
