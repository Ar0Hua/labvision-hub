package com.yupi.yupicture.application.agent;

import com.yupi.yupicture.infrastructure.mapper.AgentIndexMaintenanceMapper;
import com.yupi.yupicture.infrastructure.exception.*;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import javax.annotation.Resource;
import java.util.*;

@Service
public class AgentIndexMaintenanceService {
    @Resource private AgentServiceTokenService tokens;
    @Resource private AgentIndexMaintenanceMapper mapper;

    public List<Map<String,Object>> scan(String authorization,long after,int limit) {
        authenticate(authorization);
        if(after<0 || limit<1 || limit>100) invalid();
        return mapper.scan(after,limit);
    }

    @Transactional(rollbackFor=Exception.class)
    public int enqueue(String authorization,String runId,List<String> ids) {
        authenticate(authorization);
        if(runId==null || !runId.matches("[a-zA-Z0-9_-]{1,64}") || ids==null || ids.size()>100) invalid();
        List<Long> parsed=new ArrayList<>();
        for(String id:ids) {
            if(id==null || !id.matches("[1-9][0-9]{0,18}")) invalid();
            try { parsed.add(Long.valueOf(id)); } catch(NumberFormatException e) { invalid(); }
        }
        int added=0;
        for(Long id:new LinkedHashSet<>(parsed)) added+=mapper.enqueue(id,"maintenance:"+runId+":"+id);
        return added;
    }

    private void authenticate(String authorization) {
        if(authorization==null || !authorization.startsWith("Bearer "))
            throw new BusinessException(ErrorCode.NO_AUTH_ERROR,"索引维护令牌无效");
        tokens.verifyWorker(authorization.substring(7));
    }
    private void invalid() { throw new BusinessException(ErrorCode.PARAMS_ERROR,"非法索引维护请求"); }
}
