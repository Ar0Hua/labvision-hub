package com.yupi.yupicture;

import com.yupi.yupicture.application.agent.*;
import com.yupi.yupicture.domain.user.entity.User;
import com.yupi.yupicture.infrastructure.exception.*;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;
import java.util.*;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class AgentCitationReauthorizationTest {
    @Test void storedCitationCannotBypassCurrentPicturePermission() {
        AgentTaskEventService service=new AgentTaskEventService();
        AgentPictureService pictures=mock(AgentPictureService.class);
        ReflectionTestUtils.setField(service,"pictures",pictures);
        User user=new User();user.setId(7L);
        when(pictures.details(eq("c"),anyList(),eq(user))).thenThrow(new BusinessException(ErrorCode.NO_AUTH_ERROR,"revoked"));
        assertThrows(BusinessException.class,()->service.requireCitationAccess("c",Collections.singletonList("{\"pictureId\":\"1\"}"),user));
        verify(pictures).details("c",Collections.singletonList(1L),user);
    }
    @Test void invalidOrOversizedHistoryFailsClosed() {
        AgentTaskEventService service=new AgentTaskEventService();
        assertThrows(BusinessException.class,()->service.requireCitationAccess("c",Collections.singletonList("{}"),new User()));
        assertThrows(BusinessException.class,()->service.requireCitationAccess("c",Collections.nCopies(201,"{}"),new User()));
    }
}
