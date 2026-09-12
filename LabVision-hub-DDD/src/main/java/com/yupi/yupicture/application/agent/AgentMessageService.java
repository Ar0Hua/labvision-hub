package com.yupi.yupicture.application.agent;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.yupi.yupicture.domain.agent.AgentMessage;
import com.yupi.yupicture.domain.user.entity.User;
import com.yupi.yupicture.infrastructure.exception.*;
import com.yupi.yupicture.infrastructure.mapper.AgentMessageMapper;
import org.springframework.stereotype.Service;
import javax.annotation.Resource;
import java.util.*;
/** 保存用户可见消息；模型隐藏思维链不进入该表。 */
@Service
public class AgentMessageService {
 @Resource private AgentConversationService conversations;
 @Resource private AgentMessageMapper mapper;
 public AgentMessage createUserMessage(String conversationId,String content,User user) {
  conversations.requireOwner(conversationId,user);
  String value=content==null?"":content.trim();
  if(value.isEmpty()||value.length()>8000) throw new BusinessException(ErrorCode.PARAMS_ERROR,"消息长度必须为 1 至 8000 个字符");
  AgentMessage row=new AgentMessage(); row.setId(UUID.randomUUID().toString());
  row.setConversationId(conversationId); row.setUserId(user.getId()); row.setRole("USER"); row.setContent(value);
  if(mapper.insert(row)!=1) throw new BusinessException(ErrorCode.OPERATION_ERROR,"消息保存失败");
  return row;
 }
 public List<AgentMessage> list(String conversationId,User user) {
  conversations.requireOwner(conversationId,user);
  return mapper.selectList(new QueryWrapper<AgentMessage>().eq("conversationId",conversationId).orderByAsc("createTime").orderByAsc("id"));
 }
}
