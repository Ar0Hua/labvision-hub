package com.yupi.yupicture.interfaces.vo.agent;
import com.yupi.yupicture.domain.agent.AgentTaskEvent;
import lombok.Data;
import java.util.Date;
@Data
public class AgentTaskEventVO {
    private String eventId;
    private String eventType;
    private String payloadJson;
    private Date createTime;
    public static AgentTaskEventVO from(AgentTaskEvent event) {
        AgentTaskEventVO vo=new AgentTaskEventVO();
        vo.setEventId(event.getId()==null?null:event.getId().toString());
        vo.setEventType(event.getEventType());
        vo.setPayloadJson(event.getPayloadJson());
        vo.setCreateTime(event.getCreateTime());
        return vo;
    }
}
