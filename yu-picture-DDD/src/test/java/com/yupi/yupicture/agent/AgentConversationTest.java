package com.yupi.yupicture.agent;
import com.yupi.yupicture.application.agent.AgentConversationService;
import com.yupi.yupicture.domain.agent.AgentConversation;
import com.yupi.yupicture.domain.user.entity.User;
import com.yupi.yupicture.infrastructure.mapper.AgentConversationMapper;
import com.yupi.yupicture.infrastructure.exception.BusinessException;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.test.util.ReflectionTestUtils;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;
import java.util.*;
import com.yupi.yupicture.interfaces.vo.agent.AgentConversationVO;
class AgentConversationTest {
 @Test void ownershipAndStateFailClosed() {
  AgentConversationMapper mapper = mock(AgentConversationMapper.class);
  AgentConversationService service = new AgentConversationService();
  ReflectionTestUtils.setField(service,"mapper",mapper);
  User user = new User(); user.setId(1L);
  when(mapper.insert(any(AgentConversation.class))).thenReturn(1);
  String id = service.create(user);
  ArgumentCaptor<AgentConversation> captor = ArgumentCaptor.forClass(AgentConversation.class);
  verify(mapper).insert(captor.capture());
  AgentConversation row = captor.getValue();
  assertEquals(id,row.getId()); assertEquals(Long.valueOf(1),row.getUserId());
  when(mapper.selectById(id)).thenReturn(row);
  assertDoesNotThrow(() -> service.requireOwner(id,user));
  row.setUserId(2L);
  assertThrows(BusinessException.class,() -> service.requireOwner(id,user));
  row.setUserId(1L); row.setStatus("CLOSED");
  assertThrows(BusinessException.class,() -> service.requireOwner(id,user));
  when(mapper.selectById(id)).thenReturn(null);
  assertThrows(BusinessException.class,() -> service.requireOwner(id,user));
  clearInvocations(mapper);
  assertThrows(BusinessException.class,() -> service.requireOwner("invalid",user));
  verifyNoInteractions(mapper);
 }
 @Test void failedInsertAndAnonymousCreationRejected() {
  AgentConversationService service = new AgentConversationService();
  AgentConversationMapper mapper = mock(AgentConversationMapper.class);
  ReflectionTestUtils.setField(service,"mapper",mapper);
  User user = new User(); user.setId(1L);
  assertThrows(BusinessException.class,() -> service.create(user));
  clearInvocations(mapper);
  assertThrows(BusinessException.class,() -> service.create(null));
  verifyNoInteractions(mapper);
 }
 @Test void listReturnsOnlyMapperScopedConversationView() {
  AgentConversationService service = new AgentConversationService();
  AgentConversationMapper mapper = mock(AgentConversationMapper.class);
  ReflectionTestUtils.setField(service,"mapper",mapper);
  User user = new User(); user.setId(7L);
  AgentConversation row = new AgentConversation(); row.setId("conversation");
  row.setUserId(7L); row.setSpaceId(9L); row.setStatus("ACTIVE");
  when(mapper.selectList(any())).thenReturn(Collections.singletonList(row));

  List<AgentConversationVO> result = service.list(user);

  assertEquals(1,result.size()); assertEquals("conversation",result.get(0).getConversationId());
  assertEquals("9",result.get(0).getSpaceId()); assertEquals("ACTIVE",result.get(0).getStatus());
  verify(mapper).selectList(argThat(query -> query.getSqlSegment().contains("userId")
          && query.getSqlSegment().contains("updateTime")));
  clearInvocations(mapper);
  assertThrows(BusinessException.class,() -> service.list(null));
  verifyNoInteractions(mapper);
 }
}
