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
import java.util.List;
import java.util.stream.Collectors;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.yupi.yupicture.interfaces.vo.agent.AgentConversationVO;

/** MySQL 持久保存会话归属，每次访问检查状态和用户。 */
@Service
public class AgentConversationService {
    @Resource
    private AgentConversationMapper mapper;
    @Resource
    private AgentAccessService access;

    public String create(User user) {
        return create(user, null);
    }

    public String create(User user, Long spaceId) {
        requireUser(user);
        if (spaceId != null) {
            access.resolve(user, java.util.Collections.singletonList(spaceId));
        }
        String id = UUID.randomUUID().toString();
        AgentConversation row = new AgentConversation();
        row.setId(id);
        row.setUserId(user.getId());
        row.setStatus("ACTIVE");
        row.setSpaceId(spaceId);
        if (mapper.insert(row) != 1) {
            throw new BusinessException(ErrorCode.OPERATION_ERROR, "会话创建失败");
        }
        return id;
    }

    public AgentConversation requireOwner(String id, User user) {
        requireUser(user);
        if (id == null || !id.matches("[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")) {
            throw new BusinessException(ErrorCode.NO_AUTH_ERROR, "会话不可访问或已过期");
        }
        AgentConversation row = mapper.selectById(id);
        if (row == null || !Objects.equals(user.getId(), row.getUserId()) || !"ACTIVE".equals(row.getStatus())) {
            throw new BusinessException(ErrorCode.NO_AUTH_ERROR, "会话不可访问或已过期");
        }
        return row;
    }

    public List<AgentConversationVO> list(User user) {
        requireUser(user);
        return mapper.selectList(new QueryWrapper<AgentConversation>()
                        .eq("userId", user.getId())
                        .orderByDesc("updateTime")
                        .orderByDesc("id")
                        .last("LIMIT 50"))
                .stream().map(AgentConversationVO::from).collect(Collectors.toList());
    }

    public void requirePictureScope(String id, User user, Long pictureSpaceId) {
        AgentConversation row = requireOwner(id, user);
        if (!Objects.equals(row.getSpaceId(), pictureSpaceId)) {
            throw new BusinessException(ErrorCode.NO_AUTH_ERROR, "图片不在当前会话范围内");
        }
    }

    private void requireUser(User user) {
        if (user == null || user.getId() == null) {
            throw new BusinessException(ErrorCode.NOT_LOGIN_ERROR);
        }
    }
}
