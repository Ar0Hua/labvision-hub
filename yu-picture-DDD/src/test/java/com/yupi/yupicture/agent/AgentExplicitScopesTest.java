package com.yupi.yupicture.agent;
import com.yupi.yupicture.application.agent.AgentExplicitScopes;
import com.yupi.yupicture.infrastructure.exception.BusinessException;
import org.junit.jupiter.api.Test;
import java.util.*;
import static org.junit.jupiter.api.Assertions.*;

class AgentExplicitScopesTest {
    @Test void requiresExplicitBoundedSpaceIdsInOriginalQuery() {
        assertEquals(Arrays.asList(1L,2L),AgentExplicitScopes.comparison("比较空间 1、2 的图片数量"));
        assertEquals(Arrays.asList(1L,2L),AgentExplicitScopes.comparison("比较空间1和空间2"));
        assertTrue(AgentExplicitScopes.comparison("统计当前空间").isEmpty());
        assertThrows(BusinessException.class,()->AgentExplicitScopes.comparison("比较空间1,2,3,4,5,6"));
        assertThrows(BusinessException.class,()->AgentExplicitScopes.comparison("比较空间0,2"));
    }
}
