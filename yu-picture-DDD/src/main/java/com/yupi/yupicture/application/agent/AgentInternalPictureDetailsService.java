package com.yupi.yupicture.application.agent;

import com.yupi.yupicture.domain.user.entity.User;
import org.springframework.stereotype.Service;

import javax.annotation.Resource;
import java.util.List;
import java.util.Map;

/** 对外部索引返回的候选 ID 逐项回源鉴权，Qdrant payload 不能替代此检查。 */
@Service
public class AgentInternalPictureDetailsService {
    @Resource private AgentInternalTaskService internalTasks;
    @Resource private AgentPictureService pictures;

    public List<Map<String, Object>> details(String bearerToken, String taskId, List<Long> pictureIds) {
        Map<String, Object> context = internalTasks.context(bearerToken, taskId);
        User user = new User();
        user.setId(Long.valueOf(context.get("userId").toString()));
        return pictures.details(context.get("conversationId").toString(), pictureIds, user);
    }
}
