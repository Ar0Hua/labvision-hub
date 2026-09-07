package com.yupi.yupicture.agent;
import com.yupi.yupicture.application.agent.AgentConversationService;
import com.yupi.yupicture.domain.user.entity.User;
import com.yupi.yupicture.infrastructure.exception.BusinessException;
import org.junit.jupiter.api.Test;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.ValueOperations;
import org.springframework.test.util.ReflectionTestUtils;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;
class AgentConversationTest {
 @Test @SuppressWarnings("unchecked") void ownershipAndExpiryFailClosed() {
  AgentConversationService service = new AgentConversationService();
  StringRedisTemplate redis = mock(StringRedisTemplate.class);
  ValueOperations<String,String> values = mock(ValueOperations.class);
  when(redis.opsForValue()).thenReturn(values);
  ReflectionTestUtils.setField(service,"redis",redis);
  User user = new User(); user.setId(1L);
  String id = service.create(user);
  verify(values).set(eq("labvision:agent:conversation:owner:"+id),eq("1"),eq(java.time.Duration.ofHours(24)));
  when(values.get(anyString())).thenReturn("1","2",null);
  assertDoesNotThrow(() -> service.requireOwner(id,user));
  assertThrows(BusinessException.class,() -> service.requireOwner(id,user));
  assertThrows(BusinessException.class,() -> service.requireOwner(id,user));
  assertThrows(BusinessException.class,() -> service.requireOwner("invalid",user));
 }
}
