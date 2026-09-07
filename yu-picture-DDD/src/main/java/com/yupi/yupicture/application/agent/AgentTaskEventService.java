package com.yupi.yupicture.application.agent;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.yupi.yupicture.domain.agent.*;
import com.yupi.yupicture.domain.user.entity.User;
import com.yupi.yupicture.infrastructure.exception.*;
import com.yupi.yupicture.infrastructure.mapper.*;
import com.yupi.yupicture.interfaces.vo.agent.AgentTaskEventVO;
import org.springframework.stereotype.Service;
import javax.annotation.Resource;
import java.util.*;
import java.util.stream.Collectors;
import cn.hutool.json.JSONUtil;

@Service
public class AgentTaskEventService {
    private static final Set<String> TYPES = new HashSet<>(Arrays.asList(
            "status", "tool_start", "tool_result", "citation",
            "answer_delta", "approval_required", "done", "error"));
    @Resource private AgentTaskEventMapper mapper;
    @Resource private AgentTaskMapper tasks;
    @Resource private AgentConversationService conversations;

    /** 仅供受信任的应用服务调用；内部 HTTP 写入口将在服务认证步骤提供。 */
    public AgentTaskEvent append(String taskId, String type, String payloadJson) {
        if (taskId == null || !taskId.matches("[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
                || !TYPES.contains(type)) {
            throw new BusinessException(ErrorCode.PARAMS_ERROR, "非法任务事件");
        }
        String payload = payloadJson == null ? "{}" : payloadJson;
        if (payload.length() > 65535 || !JSONUtil.isTypeJSON(payload)) {
            throw new BusinessException(ErrorCode.PARAMS_ERROR, "任务事件内容必须是有效且不超过 65535 字符的 JSON");
        }
        AgentTaskEvent event=new AgentTaskEvent();
        event.setTaskId(taskId);
        event.setEventType(type);
        event.setPayloadJson(payload);
        if (mapper.insert(event)!=1) {
            throw new BusinessException(ErrorCode.OPERATION_ERROR, "任务事件保存失败");
        }
        return event;
    }

    public List<AgentTaskEventVO> listAfter(String taskId, Long afterEventId, Integer requestedLimit, User user) {
        AgentTask task=tasks.selectById(taskId);
        if (task==null) throw new BusinessException(ErrorCode.NO_AUTH_ERROR, "任务不可访问");
        conversations.requireOwner(task.getConversationId(),user);
        long after=afterEventId==null?0:afterEventId;
        int limit=requestedLimit==null?100:requestedLimit;
        if(after<0||limit<1||limit>200) throw new BusinessException(ErrorCode.PARAMS_ERROR,"事件游标或数量非法");
        return mapper.selectList(new QueryWrapper<AgentTaskEvent>()
                .eq("taskId",taskId).gt("id",after).orderByAsc("id").last("LIMIT "+limit))
                .stream().map(AgentTaskEventVO::from).collect(Collectors.toList());
    }
}
