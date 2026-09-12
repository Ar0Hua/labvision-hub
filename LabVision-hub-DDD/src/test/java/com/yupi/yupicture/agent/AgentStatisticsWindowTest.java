package com.yupi.yupicture.agent;
import com.yupi.yupicture.application.agent.AgentStatisticsWindow;
import com.yupi.yupicture.infrastructure.exception.BusinessException;
import java.time.LocalDate;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class AgentStatisticsWindowTest {
    @Test void explicitAndRelativeDatesAreBoundedAndUploaderIsParsed() {
        AgentStatisticsWindow f=AgentStatisticsWindow.parse(
                "统计 2026-05-01 至 2026-05-31 上传人ID 7",LocalDate.of(2026,9,9));
        assertEquals("2026-05-01",f.startDate);
        assertEquals("2026-05-31",f.endDate);
        assertEquals(Long.valueOf(7),f.uploaderId);
        AgentStatisticsWindow recent=AgentStatisticsWindow.parse("最近三个月上传数量",LocalDate.of(2026,9,9));
        assertEquals("2026-06-09",recent.startDate);
        assertThrows(BusinessException.class,()->AgentStatisticsWindow.parse(
                "2026-05-31 至 2026-05-01",LocalDate.now()));
    }
}
