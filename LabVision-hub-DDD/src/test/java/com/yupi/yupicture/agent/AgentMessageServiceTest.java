package com.yupi.yupicture.agent;
import com.baomidou.mybatisplus.core.conditions.Wrapper;
import com.yupi.yupicture.application.agent.*;
import com.yupi.yupicture.domain.agent.AgentMessage;
import com.yupi.yupicture.domain.user.entity.User;
import com.yupi.yupicture.infrastructure.exception.*;
import com.yupi.yupicture.infrastructure.mapper.AgentMessageMapper;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.test.util.ReflectionTestUtils;
import java.util.*;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class AgentMessageServiceTest {
 @Test void savesNormalizedUserMessageAfterOwnershipCheck() {
  AgentMessageService service=new AgentMessageService();
  AgentConversationService conversations=mock(AgentConversationService.class);
  AgentMessageMapper mapper=mock(AgentMessageMapper.class);
  ReflectionTestUtils.setField(service,"conversations",conversations);
  ReflectionTestUtils.setField(service,"mapper",mapper);
  User user=new User(); user.setId(9L);
  when(mapper.insert(any(AgentMessage.class))).thenReturn(1);
  AgentMessage saved=service.createUserMessage("conversation","  查询显微图  ",user);
  verify(conversations).requireOwner("conversation",user);
  ArgumentCaptor<AgentMessage> captor=ArgumentCaptor.forClass(AgentMessage.class);
  verify(mapper).insert(captor.capture());
  assertEquals("查询显微图",saved.getContent());
  assertEquals("USER",saved.getRole());
  assertEquals(Long.valueOf(9),saved.getUserId());
  assertEquals(36,saved.getId().length());
 }
 @Test void invalidOrFailedMessagesAreRejected() {
  AgentMessageService service=new AgentMessageService();
  AgentConversationService conversations=mock(AgentConversationService.class);
  AgentMessageMapper mapper=mock(AgentMessageMapper.class);
  ReflectionTestUtils.setField(service,"conversations",conversations);
  ReflectionTestUtils.setField(service,"mapper",mapper);
  User user=new User(); user.setId(1L);
  assertThrows(BusinessException.class,()->service.createUserMessage("c","   ",user));
  assertThrows(BusinessException.class,()->service.createUserMessage("c","x".repeat(8001),user));
  verifyNoInteractions(mapper);
  assertThrows(BusinessException.class,()->service.createUserMessage("c","valid",user));
 }
 @Test @SuppressWarnings("unchecked") void listChecksOwnerBeforeReading() {
  AgentMessageService service=new AgentMessageService();
  AgentConversationService conversations=mock(AgentConversationService.class);
  AgentMessageMapper mapper=mock(AgentMessageMapper.class);
  ReflectionTestUtils.setField(service,"conversations",conversations);
  ReflectionTestUtils.setField(service,"mapper",mapper);
  User user=new User(); user.setId(1L);
  when(mapper.selectList(any(Wrapper.class))).thenReturn(Collections.emptyList());
  assertTrue(service.list("c",user).isEmpty());
  verify(conversations).requireOwner("c",user);
  doThrow(new BusinessException(ErrorCode.NO_AUTH_ERROR)).when(conversations).requireOwner("other",user);
  clearInvocations(mapper);
  assertThrows(BusinessException.class,()->service.list("other",user));
  verifyNoInteractions(mapper);
 }
}
