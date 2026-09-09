package com.yupi.yupicture.application.agent;
import cn.hutool.json.JSONUtil;

import com.baomidou.mybatisplus.core.conditions.update.UpdateWrapper;
import com.yupi.yupicture.domain.agent.*;
import com.yupi.yupicture.domain.user.entity.User;
import com.yupi.yupicture.domain.user.repository.UserRepository;
import com.yupi.yupicture.infrastructure.exception.*;
import com.yupi.yupicture.infrastructure.mapper.*;
import com.yupi.yupicture.interfaces.dto.agent.AgentInternalStateRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import javax.annotation.Resource;
import java.util.*;

@Service
public class AgentInternalTaskService {
    @Resource private AgentServiceTokenService tokens;
    @Resource private AgentTaskMapper tasks;
    @Resource private AgentConversationMapper conversations;
    @Resource private AgentMessageMapper messages;
    @Resource private UserRepository users;
    @Resource private AgentAccessService access;
    @Resource private AgentTaskEventService events;

    public Map<String,Object> context(String bearerToken,String taskId) {
        AgentServiceContext signed=tokens.verify(stripBearer(bearerToken),taskId);
        AgentTask task=tasks.selectById(taskId);
        AgentConversation conversation=task==null?null:conversations.selectById(task.getConversationId());
        AgentMessage message=task==null?null:messages.selectById(task.getInputMessageId());
        User user=task==null?null:users.getById(task.getUserId());
        if(task==null||conversation==null||message==null||user==null
                ||signed.getAttempt() != (task.getRetryCount()==null?0:task.getRetryCount())
                ||!Objects.equals(task.getUserId(),conversation.getUserId())
                ||!Objects.equals(task.getUserId(),user.getId())
                ||!task.getConversationId().equals(signed.getConversationId())
                ||!task.getUserId().toString().equals(signed.getUserId())
                ||!Objects.equals(stringId(conversation.getSpaceId()),signed.getSpaceId())
                ||!task.getConversationId().equals(message.getConversationId())
                ||!"ACTIVE".equals(conversation.getStatus())
                ||!Integer.valueOf(0).equals(user.getIsDelete())) deny();
        if(conversation.getSpaceId()!=null) {
            access.resolve(user,Collections.singletonList(conversation.getSpaceId()));
        }
        Map<String,Object> result=new LinkedHashMap<>();
        result.put("taskId",taskId);
        result.put("conversationId",task.getConversationId());
        result.put("userId",task.getUserId().toString());
        result.put("spaceId",stringId(conversation.getSpaceId()));
        result.put("query",message.getContent());
        result.put("examplePictureIds",parsePictureIds(task.getExamplePictureIdsJson()));
        result.put("status",task.getStatus());
        return result;
    }

    @Transactional(rollbackFor=Exception.class)
    public void appendEvent(String bearerToken,String taskId,String type,String payload) {
        tasks.lockById(taskId);
        context(bearerToken,taskId);
        events.append(taskId,type,payload);
    }

    @Transactional(rollbackFor=Exception.class)
    public void updateState(String bearerToken,String taskId,AgentInternalStateRequest request) {
        context(bearerToken,taskId);
        if(request==null||request.getStatus()==null||request.getStage()==null
                ||!request.getStage().matches("[A-Za-z0-9_-]{1,32}")) {
            throw new BusinessException(ErrorCode.PARAMS_ERROR,"非法任务状态");
        }
        String oldStatus;
        if("RUNNING".equals(request.getStatus())) oldStatus="PENDING";
        else if("SUCCEEDED".equals(request.getStatus())||"FAILED".equals(request.getStatus())) oldStatus="RUNNING";
        else throw new BusinessException(ErrorCode.PARAMS_ERROR,"非法任务状态转换");
        String errorCode=limit(request.getErrorCode(),64);
        String errorMessage=limit(request.getErrorMessage(),512);
        int changed=tasks.update(null,new UpdateWrapper<AgentTask>().eq("id",taskId).eq("status",oldStatus)
                .set("status",request.getStatus()).set("stage",request.getStage())
                .set("errorCode",errorCode).set("errorMessage",errorMessage));
        if(changed!=1) throw new BusinessException(ErrorCode.OPERATION_ERROR,"任务状态已变化");
        String eventType="FAILED".equals(request.getStatus())?"error":
                ("SUCCEEDED".equals(request.getStatus())?"done":"status");
        events.append(taskId,eventType,"{\"status\":\""+request.getStatus()+"\",\"stage\":\""+request.getStage()+"\"}");
    }

    private List<String> parsePictureIds(String value) {
        if (value == null || value.trim().isEmpty()) return Collections.emptyList();
        try {
            List<Long> ids = JSONUtil.toList(value, Long.class);
            List<String> result = new ArrayList<>();
            for (Long id : ids) if (id != null && id > 0) result.add(id.toString());
            return result;
        } catch (RuntimeException exception) { deny(); return Collections.emptyList(); }
    }
    private String stripBearer(String value) {
        if(value==null||!value.startsWith("Bearer ")) deny();
        return value.substring(7);
    }
    private String stringId(Long value){return value==null?null:value.toString();}
    private String limit(String value,int max) {
        if(value!=null&&value.length()>max) throw new BusinessException(ErrorCode.PARAMS_ERROR,"错误信息过长");
        return value;
    }
    private void deny(){throw new BusinessException(ErrorCode.NO_AUTH_ERROR,"内部任务上下文不可访问");}
}
