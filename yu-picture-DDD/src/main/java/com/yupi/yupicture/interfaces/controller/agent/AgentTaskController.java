package com.yupi.yupicture.interfaces.controller.agent;

import com.yupi.yupicture.application.agent.AgentTaskService;
import com.yupi.yupicture.application.service.UserApplicationService;
import com.yupi.yupicture.infrastructure.common.BaseResponse;
import com.yupi.yupicture.infrastructure.common.ResultUtils;
import com.yupi.yupicture.interfaces.vo.agent.AgentTaskVO;
import com.yupi.yupicture.application.agent.AgentTaskEventService;
import com.yupi.yupicture.application.agent.AgentTaskEventStreamService;
import com.yupi.yupicture.interfaces.vo.agent.AgentTaskEventVO;
import org.springframework.web.bind.annotation.*;
import javax.annotation.Resource;
import javax.servlet.http.HttpServletRequest;
import java.util.List;
import org.springframework.http.MediaType;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

@RestController
@RequestMapping("/agent/tasks")
public class AgentTaskController {
    @Resource private AgentTaskService tasks;
    @Resource private UserApplicationService users;
    @Resource private AgentTaskEventService events;
    @Resource private AgentTaskEventStreamService eventStream;

    @GetMapping("/{id}")
    public BaseResponse<AgentTaskVO> get(@PathVariable String id, HttpServletRequest request) {
        return ResultUtils.success(tasks.get(id, users.getLoginUser(request)));
    }

    @PostMapping("/{id}/cancel")
    public BaseResponse<AgentTaskVO> cancel(@PathVariable String id, HttpServletRequest request) {
        return ResultUtils.success(tasks.cancel(id, users.getLoginUser(request)));
    }

    @PostMapping("/{id}/resume")
    public BaseResponse<AgentTaskVO> resume(@PathVariable String id, HttpServletRequest request) {
        return ResultUtils.success(tasks.resume(id, users.getLoginUser(request)));
    }

    @GetMapping("/{id}/events/history")
    public BaseResponse<List<AgentTaskEventVO>> events(@PathVariable String id,
            @RequestParam(required=false) Long afterEventId,
            @RequestParam(required=false) Integer limit, HttpServletRequest request) {
        return ResultUtils.success(events.listAfter(id, afterEventId, limit, users.getLoginUser(request)));
    }

    @GetMapping(value="/{id}/events", produces=MediaType.TEXT_EVENT_STREAM_VALUE)
    public SseEmitter stream(@PathVariable String id,
            @RequestHeader(value="Last-Event-ID", required=false) String lastEventId,
            @RequestParam(required=false) Long afterEventId, HttpServletRequest request) {
        long cursor=eventStream.parseCursor(lastEventId,afterEventId);
        com.yupi.yupicture.domain.user.entity.User user=users.getLoginUser(request);
        eventStream.authorize(id,cursor,user);
        SseEmitter emitter=new SseEmitter(30_000L);
        eventStream.stream(emitter,id,cursor,user);
        return emitter;
    }
}
