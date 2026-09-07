package com.yupi.yupicture.interfaces.controller.agent;

import com.yupi.yupicture.application.agent.AgentInternalTaskService;
import com.yupi.yupicture.infrastructure.common.*;
import com.yupi.yupicture.interfaces.dto.agent.*;
import org.springframework.web.bind.annotation.*;
import javax.annotation.Resource;
import java.util.Map;

@RestController
@RequestMapping("/agent/internal/tasks")
public class AgentInternalController {
    @Resource private AgentInternalTaskService internal;

    @GetMapping("/{id}/context")
    public BaseResponse<Map<String,Object>> context(@PathVariable String id,
            @RequestHeader("Authorization") String authorization) {
        return ResultUtils.success(internal.context(authorization,id));
    }
    @PostMapping("/{id}/events")
    public BaseResponse<Boolean> event(@PathVariable String id,@RequestHeader("Authorization") String authorization,
            @RequestBody AgentInternalEventRequest body) {
        internal.appendEvent(authorization,id,body.getEventType(),body.getPayloadJson());
        return ResultUtils.success(true);
    }
    @PostMapping("/{id}/state")
    public BaseResponse<Boolean> state(@PathVariable String id,@RequestHeader("Authorization") String authorization,
            @RequestBody AgentInternalStateRequest body) {
        internal.updateState(authorization,id,body);
        return ResultUtils.success(true);
    }
}
