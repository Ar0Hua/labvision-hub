package com.yupi.yupicture.application.agent;

import com.yupi.yupicture.domain.user.entity.User;
import com.yupi.yupicture.infrastructure.exception.BusinessException;
import com.yupi.yupicture.infrastructure.exception.ErrorCode;
import com.yupi.yupicture.domain.agent.AgentConversation;
import com.yupi.yupicture.infrastructure.mapper.AgentConversationMapper;
import org.springframework.stereotype.Service;
import javax.annotation.Resource;
import java.util.Objects;
import java.util.UUID;

/** MySQL 持久保存会话归属，每次访问检查状态和用户。 */
@Service
public class AgentConversationService {
    @Resource
    private AgentConversationMapper mapper;

    public String create(User user) {
        requireUser(user);
        String id = UUID.randomUUID().toString();
        AgentConversation row = new AgentConversation();
        row.setId(id);
        row.setUserId(user.getId());
        row.setStatus("ACTIVE");
        if (mapper.insert(row) != 1) {
            throw new BusinessException(ErrorCode.OPERATION_ERROR, "会话创建失败");
        }
        return id;
    }

    public void requireOwner(String id, User user) {
        requireUser(user);
        if (id == null || !id.matches("[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")) {
            throw new BusinessException(ErrorCode.NO_AUTH_ERROR, "会话不可访问或已过期");
        }
        AgentConversation row = mapper.selectById(id);
        if (row == null || !Objects.equals(user.getId(), row.getUserId()) || !"ACTIVE".equals(row.getStatus())) {
            throw new BusinessException(ErrorCode.NO_AUTH_ERROR, "会话不可访问或已过期");
        }
    }

    private void requireUser(User user) {
        if (user == null || user.getId() == null) {
            throw new BusinessException(ErrorCode.NOT_LOGIN_ERROR);
        }
    }
}
