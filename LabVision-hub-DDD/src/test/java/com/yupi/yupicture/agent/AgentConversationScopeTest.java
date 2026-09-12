package com.yupi.yupicture.agent;
import com.yupi.yupicture.application.agent.*;
import com.yupi.yupicture.domain.agent.AgentConversation;
import com.yupi.yupicture.domain.user.entity.User;
import com.yupi.yupicture.infrastructure.mapper.AgentConversationMapper;
import com.yupi.yupicture.infrastructure.exception.*;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.test.util.ReflectionTestUtils;
import java.util.Collections;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class AgentConversationScopeTest {
 @Test void creationChecksScopeAndReadCannotCrossIt() {
  AgentConversationService service = new AgentConversationService();
  AgentConversationMapper mapper = mock(AgentConversationMapper.class);
  AgentAccessService access = mock(AgentAccessService.class);
  ReflectionTestUtils.setField(service,"mapper",mapper);
  ReflectionTestUtils.setField(service,"access",access);
  User user = new User(); user.setId(1L);
  when(mapper.insert(any(AgentConversation.class))).thenReturn(1);
  String id = service.create(user,7L);
  verify(access).resolve(user,Collections.singletonList(7L));
  ArgumentCaptor<AgentConversation> captor = ArgumentCaptor.forClass(AgentConversation.class);
  verify(mapper).insert(captor.capture());
  AgentConversation row = captor.getValue();
  assertEquals(Long.valueOf(7),row.getSpaceId());
  when(mapper.selectById(id)).thenReturn(row);
  assertDoesNotThrow(() -> service.requirePictureScope(id,user,7L));
  assertThrows(BusinessException.class,() -> service.requirePictureScope(id,user,8L));
  assertThrows(BusinessException.class,() -> service.requirePictureScope(id,user,null));
  row.setSpaceId(null);
  assertDoesNotThrow(() -> service.requirePictureScope(id,user,null));
  assertThrows(BusinessException.class,() -> service.requirePictureScope(id,user,7L));
  when(access.resolve(user,Collections.singletonList(8L))).thenThrow(new BusinessException(ErrorCode.NO_AUTH_ERROR));
  clearInvocations(mapper);
  assertThrows(BusinessException.class,() -> service.create(user,8L));
  verifyNoInteractions(mapper);
 }
}
