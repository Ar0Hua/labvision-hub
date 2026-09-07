package com.yupi.yupicture.interfaces.controller.agent;

import com.yupi.yupicture.application.agent.AgentTaskService;
import com.yupi.yupicture.application.service.UserApplicationService;
import com.yupi.yupicture.infrastructure.common.BaseResponse;
import com.yupi.yupicture.infrastructure.common.ResultUtils;
import com.yupi.yupicture.interfaces.vo.agent.AgentTaskVO;
import com.yupi.yupicture.application.agent.AgentTaskEventService;
import com.yupi.yupicture.interfaces.vo.agent.AgentTaskEventVO;
import org.springframework.web.bind.annotation.*;
import javax.annotation.Resource;
import javax.servlet.http.HttpServletRequest;
import java.util.List;

@RestController
@RequestMapping("/agent/tasks")
public class AgentTaskController {
    @Resource private AgentTaskService tasks;
    @Resource private UserApplicationService users;
    @Resource private AgentTaskEventService events;

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

    @GetMapping("/{id}/events")
    public BaseResponse<List<AgentTaskEventVO>> events(@PathVariable String id,
            @RequestParam(required=false) Long afterEventId,
            @RequestParam(required=false) Integer limit, HttpServletRequest request) {
        return ResultUtils.success(events.listAfter(id, afterEventId, limit, users.getLoginUser(request)));
    }
}
