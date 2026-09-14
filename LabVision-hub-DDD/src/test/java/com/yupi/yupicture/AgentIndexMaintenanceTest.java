package com.yupi.yupicture;
import com.yupi.yupicture.application.agent.*;
import com.yupi.yupicture.infrastructure.mapper.AgentIndexMaintenanceMapper;
import com.yupi.yupicture.infrastructure.exception.BusinessException;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;
import java.util.*;
import static org.mockito.Mockito.*;
import static org.junit.jupiter.api.Assertions.*;

class AgentIndexMaintenanceTest {
    @Test void validatesBeforeEnqueueAndDeduplicates() {
        AgentIndexMaintenanceService service=new AgentIndexMaintenanceService();
        AgentServiceTokenService tokens=mock(AgentServiceTokenService.class);
        AgentIndexMaintenanceMapper mapper=mock(AgentIndexMaintenanceMapper.class);
        ReflectionTestUtils.setField(service,"tokens",tokens);
        ReflectionTestUtils.setField(service,"mapper",mapper);
        assertThrows(BusinessException.class,()->service.scan(null,0,10));
        assertThrows(BusinessException.class,()->service.scan("Bearer token",0,101));
        assertThrows(BusinessException.class,()->service.enqueue("Bearer token","r",Arrays.asList("1","bad")));
        verifyNoInteractions(mapper);
        service.enqueue("Bearer token","r",Arrays.asList("1","1"));
        verify(mapper,times(1)).enqueue(1L,"maintenance:r:1");
    }
}
