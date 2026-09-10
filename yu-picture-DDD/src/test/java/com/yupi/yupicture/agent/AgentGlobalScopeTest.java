package com.yupi.yupicture.agent;
import com.yupi.yupicture.application.agent.*;
import com.yupi.yupicture.domain.agent.AgentConversation;
import com.yupi.yupicture.domain.user.entity.User;
import com.yupi.yupicture.infrastructure.mapper.AgentConversationMapper;
import com.yupi.yupicture.infrastructure.exception.*;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;
import java.util.*;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class AgentGlobalScopeTest {
    @Test void snapshotRestrictsResourcesAndRevocationBlocksHistory() {
        String id="11111111-1111-1111-1111-111111111111";
        User user=new User();user.setId(1L);
        AgentConversation row=new AgentConversation();row.setId(id);row.setUserId(1L);row.setStatus("ACTIVE");
        row.setAllSpaces(true);row.setScopeSpaceIdsJson("[9,10]");
        AgentConversationMapper mapper=mock(AgentConversationMapper.class);
        when(mapper.selectById(id)).thenReturn(row);
        AgentAccessService access=mock(AgentAccessService.class);
        AgentConversationService service=new AgentConversationService();
        ReflectionTestUtils.setField(service,"mapper",mapper);ReflectionTestUtils.setField(service,"access",access);
        assertDoesNotThrow(()->service.requirePictureScope(id,user,9L));
        assertDoesNotThrow(()->service.requirePictureScope(id,user,null));
        assertThrows(BusinessException.class,()->service.requirePictureScope(id,user,11L));
        when(access.resolve(user,Arrays.asList(9L,10L))).thenThrow(new BusinessException(ErrorCode.NO_AUTH_ERROR));
        assertThrows(BusinessException.class,()->service.requireOwner(id,user));
        assertThrows(BusinessException.class,()->service.create(user,9L,true));
    }
}
