package com.yupi.yupicture.application.agent;
import cn.hutool.json.JSONUtil;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.yupi.yupicture.domain.agent.AgentTaskEvent;
import com.yupi.yupicture.domain.user.entity.User;
import com.yupi.yupicture.infrastructure.mapper.AgentTaskEventMapper;
import com.yupi.yupicture.infrastructure.mapper.AgentFeedbackMapper;
import com.yupi.yupicture.infrastructure.exception.*;
import com.yupi.yupicture.interfaces.vo.agent.AgentTaskVO;
import org.springframework.stereotype.Service;
import javax.annotation.Resource;
import java.util.*;

@Service
public class AgentFeedbackService {
    @Resource private AgentTaskService tasks;
    @Resource private AgentPictureService pictures;
    @Resource private AgentTaskEventMapper events;
    @Resource private AgentFeedbackMapper feedback;

    public void save(String taskId, Long pictureId, String label, User user) {
        AgentTaskVO task = tasks.get(taskId, user);
        if (pictureId == null || pictureId <= 0 || !Arrays.asList(
                "relevant","irrelevant","duplicate","permission_issue").contains(label)) {
            throw new BusinessException(ErrorCode.PARAMS_ERROR, "反馈参数无效");
        }
        List<AgentTaskEvent> citations = events.selectList(new QueryWrapper<AgentTaskEvent>()
                .eq("taskId",taskId).eq("eventType","citation").orderByDesc("id").last("LIMIT 200"));
        boolean cited = citations.stream().anyMatch(event ->
                pictureId.toString().equals(JSONUtil.parseObj(event.getPayloadJson()).getStr("pictureId")));
        if (!cited) throw new BusinessException(ErrorCode.NO_AUTH_ERROR, "只能反馈本任务引用图片");
        // Permission issue reports must remain possible after the picture becomes inaccessible.
        if (!"permission_issue".equals(label)) {
            pictures.details(task.getConversationId(), Collections.singletonList(pictureId), user);
        }
        feedback.save(taskId, user.getId(), pictureId, label);
    }

    public List<Map<String,Object>> list(String taskId, User user) {
        tasks.get(taskId, user);
        return feedback.list(taskId, user.getId());
    }
}
