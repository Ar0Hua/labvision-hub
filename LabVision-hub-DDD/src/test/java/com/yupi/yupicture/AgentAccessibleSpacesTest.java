package com.yupi.yupicture;

import com.yupi.yupicture.application.agent.AgentAccessService;
import com.yupi.yupicture.domain.space.entity.Space;
import com.yupi.yupicture.domain.space.repository.SpaceRepository;
import com.yupi.yupicture.domain.user.entity.User;
import com.yupi.yupicture.infrastructure.mapper.AgentScopeCandidatesMapper;
import com.yupi.yupicture.shared.auth.SpaceUserAuthManager;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;
import java.util.*;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class AgentAccessibleSpacesTest {
    @Test void onlyCurrentlyViewableSpacesReturnNamesAndPermissions() {
        AgentAccessService service = new AgentAccessService();
        SpaceRepository spaces = mock(SpaceRepository.class);
        SpaceUserAuthManager auth = mock(SpaceUserAuthManager.class);
        AgentScopeCandidatesMapper candidates = mock(AgentScopeCandidatesMapper.class);
        ReflectionTestUtils.setField(service,"spaceRepository",spaces);
        ReflectionTestUtils.setField(service,"authManager",auth);
        ReflectionTestUtils.setField(service,"scopeCandidates",candidates);
        User user = new User(); user.setId(7L); user.setUserRole("user");
        Space visible = new Space(); visible.setId(1L); visible.setSpaceName("实验室空间"); visible.setSpaceType(1);
        visible.setTotalCount(8L); visible.setTotalSize(1024L); visible.setMaxCount(10L); visible.setMaxSize(2048L);
        Space denied = new Space(); denied.setId(2L);
        when(candidates.candidates(7L,false)).thenReturn(Arrays.asList(1L,2L,3L));
        when(spaces.getById(1L)).thenReturn(visible);
        when(spaces.getById(2L)).thenReturn(denied);
        when(auth.getPermissionList(visible,user)).thenReturn(Arrays.asList("picture:view","picture:upload"));
        when(auth.getPermissionList(denied,user)).thenReturn(Collections.emptyList());
        List<Map<String,Object>> result = service.viewableSpaces(user);
        assertEquals(1,result.size());
        assertEquals("实验室空间",result.get(0).get("spaceName"));
        assertEquals(8L,result.get(0).get("totalCount"));
        assertEquals(1024L,result.get(0).get("totalSize"));
        assertEquals(10L,result.get(0).get("maxCount"));
        assertEquals(2048L,result.get(0).get("maxSize"));
        assertEquals("1",result.get(0).get("spaceId"));
        when(auth.getPermissionList(visible,user)).thenReturn(Collections.emptyList());
        assertTrue(service.viewableSpaces(user).isEmpty());
    }
}
