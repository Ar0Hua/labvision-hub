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
import com.baomidou.mybatisplus.core.conditions.update.UpdateWrapper;
import com.yupi.yupicture.domain.agent.AgentTask;
import com.yupi.yupicture.infrastructure.mapper.AgentTaskMapper;
import org.springframework.transaction.annotation.Transactional;
import com.yupi.yupicture.interfaces.vo.agent.AgentConversationVO;

/** MySQL 持久保存会话归属，每次访问检查状态和用户。 */
@Service
public class AgentConversationService {
    @Resource
    private AgentConversationMapper mapper;
    @Resource
    private AgentAccessService access;
    @Resource private AgentTaskMapper taskMapper;

    public void rename(String id, String title, User user) {
        requireUser(user);
        String normalized = title == null ? "" : title.trim();
        if (normalized.isEmpty() || normalized.length() > 60 || normalized.chars().anyMatch(Character::isISOControl)) {
            throw new BusinessException(ErrorCode.PARAMS_ERROR, "对话名称须为1至60个字符，不能包含换行或控制字符");
        }
        int changed = mapper.update(null, new UpdateWrapper<AgentConversation>()
                .eq("id", id).eq("userId", user.getId()).eq("status", "ACTIVE")
                .set("title", normalized).set("updateTime", new java.util.Date()));
        if (changed != 1) throw new BusinessException(ErrorCode.NO_AUTH_ERROR, "对话不存在或不可修改");
    }

    @Transactional(rollbackFor = Exception.class)
    public void remove(String id, User user) {
        requireUser(user);
        int changed = mapper.update(null, new UpdateWrapper<AgentConversation>()
                .eq("id", id).eq("userId", user.getId()).eq("status", "ACTIVE")
                .set("status", "DELETED").set("updateTime", new java.util.Date()));
        if (changed != 1) throw new BusinessException(ErrorCode.NO_AUTH_ERROR, "对话不存在或不可删除");
        taskMapper.update(null, new UpdateWrapper<AgentTask>()
                .eq("conversationId", id).eq("userId", user.getId()).in("status", "PENDING", "RUNNING")
                .set("status", "CANCELLED").set("stage", "CANCELLED"));
    }

    public String create(User user) {
        return create(user, null);
    }

    public String create(User user, Long spaceId) {
        return create(user,spaceId,false);
    }

    public String create(User user, Long spaceId, boolean allSpaces) {
        requireUser(user);
        if(allSpaces && spaceId!=null) throw new BusinessException(ErrorCode.PARAMS_ERROR,"全范围与指定空间不能同时选择");
        if (spaceId != null) {
            access.resolve(user, java.util.Collections.singletonList(spaceId));
        }
        String id = UUID.randomUUID().toString();
        AgentConversation row = new AgentConversation();
        row.setId(id);
        row.setUserId(user.getId());
        row.setStatus("ACTIVE");
        row.setSpaceId(spaceId);
        row.setAllSpaces(allSpaces);
        if(allSpaces) row.setScopeSpaceIdsJson(cn.hutool.json.JSONUtil.toJsonStr(access.allViewableSpaceIds(user)));
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
        if (row.getSpaceId() != null) access.resolve(user, java.util.Collections.singletonList(row.getSpaceId()));
        if (Boolean.TRUE.equals(row.getAllSpaces())) access.resolve(user,snapshot(row));
        return row;
    }

    public List<AgentConversationVO> list(User user) {
        requireUser(user);
        return mapper.selectList(new QueryWrapper<AgentConversation>()
                        .eq("userId", user.getId())
                        .eq("status", "ACTIVE")
                        .orderByDesc("updateTime")
                        .orderByDesc("id")
                        .last("LIMIT 50"))
                .stream().map(AgentConversationVO::from).collect(Collectors.toList());
    }

    public void requirePictureScope(String id, User user, Long pictureSpaceId) {
        AgentConversation row = requireOwner(id, user);
        if (Boolean.TRUE.equals(row.getAllSpaces())) {
            if(pictureSpaceId==null || snapshot(row).contains(pictureSpaceId)) return;
            throw new BusinessException(ErrorCode.NO_AUTH_ERROR,"图片不在会话授权快照内，请新建会话");
        }
        if (!Objects.equals(row.getSpaceId(), pictureSpaceId)) {
            throw new BusinessException(ErrorCode.NO_AUTH_ERROR, "图片不在当前会话范围内");
        }
    }

    private void requireUser(User user) {
        if (user == null || user.getId() == null) {
            throw new BusinessException(ErrorCode.NOT_LOGIN_ERROR);
        }
    }

    public static List<Long> snapshot(AgentConversation row) {
        try {
            List<Long> ids=cn.hutool.json.JSONUtil.toList(row.getScopeSpaceIdsJson(),Long.class);
            if(ids==null || ids.size()>50 || ids.stream().anyMatch(id->id==null || id<=0)) throw new IllegalArgumentException();
            return ids;
        } catch(RuntimeException error) {
            throw new BusinessException(ErrorCode.NO_AUTH_ERROR,"会话范围不可用，请新建会话");
        }
    }
}
