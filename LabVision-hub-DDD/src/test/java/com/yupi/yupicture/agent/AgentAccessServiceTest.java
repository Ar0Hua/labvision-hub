package com.yupi.yupicture.agent;

import com.yupi.yupicture.application.agent.AgentAccessService;
import com.yupi.yupicture.domain.space.entity.Space;
import com.yupi.yupicture.domain.space.repository.SpaceRepository;
import com.yupi.yupicture.domain.user.entity.User;
import com.yupi.yupicture.infrastructure.exception.BusinessException;
import com.yupi.yupicture.shared.auth.SpaceUserAuthManager;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;
import java.util.*;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class AgentAccessServiceTest {
    @Test
    void scopeIsRevalidatedAndIdsRemainStrings() {
        AgentAccessService service = new AgentAccessService();
        SpaceRepository repo = mock(SpaceRepository.class);
        SpaceUserAuthManager auth = mock(SpaceUserAuthManager.class);
        ReflectionTestUtils.setField(service, "spaceRepository", repo);
        ReflectionTestUtils.setField(service, "authManager", auth);
        User user = new User();
        user.setId(2059881449783808001L);
        Space space = new Space();
        when(repo.getById(1L)).thenReturn(space);
        when(auth.getPermissionList(space, user)).thenReturn(Collections.singletonList("picture:view"));
        Map<String, Object> scope = service.resolve(user, Arrays.asList(1L, 1L));
        assertEquals("2059881449783808001", scope.get("userId"));
        assertEquals(Collections.singletonList("1"), scope.get("allowedSpaceIds"));
        when(auth.getPermissionList(space, user)).thenReturn(Collections.emptyList());
        assertThrows(BusinessException.class, () -> service.resolve(user, Collections.singletonList(1L)));
        assertThrows(BusinessException.class, () -> service.resolve(user, Collections.singletonList(2L)));
    }

    @Test
    void rejectsAnonymousAndInvalidInput() {
        AgentAccessService service = new AgentAccessService();
        assertThrows(BusinessException.class, () -> service.resolve(null, Collections.emptyList()));
        User user = new User(); user.setId(1L);
        assertThrows(BusinessException.class, () -> service.resolve(user, Collections.nCopies(51, 1L)));
        assertThrows(BusinessException.class, () -> service.resolve(user, Collections.singletonList(0L)));
    }
}
