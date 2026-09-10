package com.yupi.yupicture.agent;
import com.yupi.yupicture.infrastructure.mapper.AgentStatisticsWindowMapper;
import org.apache.ibatis.annotations.Select;
import org.junit.jupiter.api.Test;
import java.lang.reflect.Method;
import java.util.Arrays;
import static org.junit.jupiter.api.Assertions.*;

class AgentWindowDistributionSqlTest {
    @Test void everyDistributionUsesSameBoundScopeAndWindow() {
        for (Method method: AgentStatisticsWindowMapper.class.getDeclaredMethods()) {
            Select select=method.getAnnotation(Select.class);
            assertNotNull(select);
            String sql=String.join(" ",select.value());
            for (String required: Arrays.asList("#{spaceId}","#{start}","#{end}","#{uploaderId}","p.isDelete=0","p.reviewStatus=1"))
                assertTrue(sql.contains(required),method.getName()+" missing "+required);
            assertFalse(sql.contains("${"));
        }
    }
}
