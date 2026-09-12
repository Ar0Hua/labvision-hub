package com.yupi.yupicture.agent;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.yupi.yupicture.application.agent.AgentVisualSearchFilters;
import com.yupi.yupicture.domain.picture.entity.Picture;
import com.yupi.yupicture.interfaces.dto.agent.AgentInternalSearchRequest;
import com.yupi.yupicture.infrastructure.exception.BusinessException;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class AgentVisualSearchFiltersTest {
    @Test void validatesAndBindsColorRangeWithCurrentBrightness() {
        AgentInternalSearchRequest request=new AgentInternalSearchRequest();
        request.setTargetColor("#ff0000"); request.setColorTolerance(10); request.setBrightness("dark");
        QueryWrapper<Picture> query=new QueryWrapper<>(); query.eq("spaceId",9L).eq("isDelete",0);
        AgentVisualSearchFilters.apply(query,request);
        String sql=query.getSqlSegment();
        assertTrue(sql.contains("spaceId"));
        assertTrue(sql.contains("REGEXP"));
        assertTrue(sql.contains("f.brightnessScore < 50"));
        assertTrue(sql.contains("sourceUpdatedAt"));
        assertTrue(sql.contains("indexStatus='READY'"));
        assertTrue(query.getParamNameValuePairs().containsValue(245));
        request.setBrightness("dark OR 1=1");
        assertThrows(BusinessException.class,()->AgentVisualSearchFilters.validate(request));
        request.setBrightness(null); request.setTargetColor("red");
        assertThrows(BusinessException.class,()->AgentVisualSearchFilters.validate(request));
        request.setTargetColor(null); request.setColorTolerance(256);
        assertThrows(BusinessException.class,()->AgentVisualSearchFilters.validate(request));
    }
}
