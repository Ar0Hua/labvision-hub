package com.yupi.yupicture.agent;

import com.baomidou.mybatisplus.core.conditions.Wrapper;
import com.yupi.yupicture.application.agent.*;
import com.yupi.yupicture.domain.agent.AgentPictureIndexOutbox;
import com.yupi.yupicture.domain.picture.entity.Picture;
import com.yupi.yupicture.domain.picture.repository.PictureRepository;
import com.yupi.yupicture.infrastructure.exception.BusinessException;
import com.yupi.yupicture.infrastructure.mapper.AgentPictureIndexOutboxMapper;
import com.yupi.yupicture.interfaces.dto.agent.AgentIndexAckRequest;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.*;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class AgentPictureIndexJobServiceTest {
    @Test void claimReturnsCurrentSnapshotAndLease() {
        Fixture f=fixture();
        AgentPictureIndexOutbox row=new AgentPictureIndexOutbox();
        row.setId(11L); row.setPictureId(2059881449783808001L); row.setStatus("PENDING"); row.setAttemptCount(0);
        when(f.jobs.selectList(any(Wrapper.class))).thenReturn(Collections.singletonList(row));
        when(f.jobs.updateById(row)).thenReturn(1);
        Picture picture=new Picture(); picture.setId(row.getPictureId()); picture.setSpaceId(9L);
        picture.setName("显微图"); picture.setIsDelete(0);
        when(f.pictures.getById(row.getPictureId())).thenReturn(picture);
        List<Map<String,Object>> result=f.service.claim("Bearer worker",10);
        assertEquals("space:9",result.get(0).get("scopeKey"));
        assertEquals("2059881449783808001",result.get(0).get("pictureId"));
        assertTrue(result.get(0).get("leaseToken").toString().matches("[0-9a-f-]{36}"));
        verify(f.tokens).verifyWorker("worker");
    }

    @Test void acknowledgementRequiresMatchingLeaseAndBacksOffFailure() {
        Fixture f=fixture();
        AgentPictureIndexOutbox row=new AgentPictureIndexOutbox();
        row.setId(11L); row.setStatus("PROCESSING"); row.setLeaseToken("11111111-1111-1111-1111-111111111111");
        row.setAttemptCount(2);
        when(f.jobs.selectById(11L)).thenReturn(row);
        when(f.jobs.update(isNull(),any(Wrapper.class))).thenReturn(1);
        AgentIndexAckRequest request=new AgentIndexAckRequest();
        request.setLeaseToken(row.getLeaseToken()); request.setSuccess(false); request.setErrorMessage("temporary\nerror");
        f.service.acknowledge("Bearer worker",11L,request);
        verify(f.jobs).update(isNull(),any(Wrapper.class));
        request.setLeaseToken("22222222-2222-2222-2222-222222222222");
        assertThrows(BusinessException.class,()->f.service.acknowledge("Bearer worker",11L,request));
    }

    private Fixture fixture(){
        Fixture f=new Fixture(); f.service=new AgentPictureIndexJobService();
        f.tokens=mock(AgentServiceTokenService.class); f.jobs=mock(AgentPictureIndexOutboxMapper.class);
        f.pictures=mock(PictureRepository.class);
        ReflectionTestUtils.setField(f.service,"tokens",f.tokens);
        ReflectionTestUtils.setField(f.service,"jobs",f.jobs);
        ReflectionTestUtils.setField(f.service,"pictures",f.pictures);
        return f;
    }
    private static class Fixture { AgentPictureIndexJobService service; AgentServiceTokenService tokens;
        AgentPictureIndexOutboxMapper jobs; PictureRepository pictures; }
}
