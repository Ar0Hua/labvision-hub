package com.yupi.yupicture.agent;
import com.yupi.yupicture.application.agent.*;
import com.yupi.yupicture.domain.picture.entity.Picture;
import com.yupi.yupicture.domain.picture.repository.PictureRepository;
import com.yupi.yupicture.domain.user.entity.User;
import com.yupi.yupicture.infrastructure.exception.*;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;
import java.util.*;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;
class AgentPictureTest {
 @Test void deniedPicturesNeverReturnMetadata() {
  AgentPictureService service = new AgentPictureService();
  AgentConversationService conversations = mock(AgentConversationService.class);
  AgentAccessService access = mock(AgentAccessService.class);
  PictureRepository repo = mock(PictureRepository.class);
  ReflectionTestUtils.setField(service,"conversations",conversations);
  ReflectionTestUtils.setField(service,"access",access);
  ReflectionTestUtils.setField(service,"pictures",repo);
  User user = new User(); user.setId(1L);
  Picture pic = new Picture(); pic.setIsDelete(0); pic.setReviewStatus(1);
  when(repo.getById(1L)).thenReturn(pic);
  List<Long> ids = Collections.singletonList(1L);
  assertFalse(service.details("c",ids,user).get(0).containsKey("url"));
  pic.setReviewStatus(0);
  assertThrows(BusinessException.class,() -> service.details("c",ids,user));
  pic.setSpaceId(2L);
  service.details("c",ids,user);
  verify(access).resolve(user,Collections.singletonList(2L));
  when(access.resolve(user,Collections.singletonList(2L))).thenThrow(new BusinessException(ErrorCode.NO_AUTH_ERROR));
  assertThrows(BusinessException.class,() -> service.details("c",ids,user));
  pic.setIsDelete(1);
  assertThrows(BusinessException.class,() -> service.details("c",ids,user));
  doThrow(new BusinessException(ErrorCode.NO_AUTH_ERROR)).when(conversations).requireOwner("other",user);
  clearInvocations(repo);
  assertThrows(BusinessException.class,() -> service.details("other",ids,user));
  verifyNoInteractions(repo);
 }
}
