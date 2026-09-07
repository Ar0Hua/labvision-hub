package com.yupi.yupicture.agent;

import com.yupi.yupicture.application.agent.*;
import com.yupi.yupicture.infrastructure.exception.BusinessException;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;
import java.time.*;
import static org.junit.jupiter.api.Assertions.*;

class AgentServiceTokenServiceTest {
    @Test void tokenIsBoundToTaskAndPreservesLargeIds() {
        AgentServiceTokenService service=service(Instant.parse("2026-09-07T00:00:00Z"));
        String token=service.issue("task","conversation",2059881449783808001L,2060208764149547009L);
        AgentServiceContext context=service.verify(token,"task");
        assertEquals("2059881449783808001",context.getUserId());
        assertEquals("2060208764149547009",context.getSpaceId());
        assertThrows(BusinessException.class,()->service.verify(token,"other"));
        String tampered=(token.charAt(0)=='a'?"b":"a")+token.substring(1);
        assertThrows(BusinessException.class,()->service.verify(tampered,"task"));
    }

    @Test void expiredMalformedAndWeakSecretAreRejected() {
        AgentServiceTokenService issuer=service(Instant.parse("2026-09-07T00:00:00Z"));
        String token=issuer.issue("task","conversation",1L,null);
        AgentServiceTokenService later=service(Instant.parse("2026-09-07T00:05:01Z"));
        assertThrows(BusinessException.class,()->later.verify(token,"task"));
        assertThrows(BusinessException.class,()->issuer.verify("bad-token","task"));
        AgentServiceTokenService weak=new AgentServiceTokenService();
        ReflectionTestUtils.setField(weak,"secret","short");
        assertThrows(BusinessException.class,()->weak.issue("t","c",1L,null));
    }

    @Test void workerTokenHasSeparatePurposeAndShortLifetime() {
        AgentServiceTokenService service=service(Instant.parse("2026-09-07T00:00:00Z"));
        String token=service.issueWorker();
        assertEquals("picture-index-worker",service.verifyWorker(token).getPurpose());
        assertThrows(BusinessException.class,()->service.verify(token,"task"));
        AgentServiceTokenService later=service(Instant.parse("2026-09-07T00:01:01Z"));
        assertThrows(BusinessException.class,()->later.verifyWorker(token));
    }

    private AgentServiceTokenService service(Instant now) {
        AgentServiceTokenService service=new AgentServiceTokenService();
        ReflectionTestUtils.setField(service,"secret","0123456789abcdef0123456789abcdef");
        ReflectionTestUtils.setField(service,"clock",Clock.fixed(now,ZoneOffset.UTC));
        return service;
    }
}
