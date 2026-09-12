package com.yupi.yupicture.interfaces.controller.agent;
import com.yupi.yupicture.application.agent.AgentFeedbackService;
import com.yupi.yupicture.application.service.UserApplicationService;
import com.yupi.yupicture.infrastructure.common.*;
import lombok.Data;
import org.springframework.web.bind.annotation.*;
import javax.annotation.Resource;
import javax.servlet.http.HttpServletRequest;
import java.util.*;

@RestController
@RequestMapping("/agent/tasks")
public class AgentFeedbackController {
    @Resource private AgentFeedbackService feedback;
    @Resource private UserApplicationService users;
    @Data public static class Request { private Long pictureId; private String label; }
    @PostMapping("/{id}/feedback")
    public BaseResponse<Boolean> save(@PathVariable String id, @RequestBody Request body,
                                     HttpServletRequest request) {
        feedback.save(id, body.getPictureId(), body.getLabel(), users.getLoginUser(request));
        return ResultUtils.success(true);
    }
    @GetMapping("/{id}/feedback")
    public BaseResponse<List<Map<String,Object>>> list(@PathVariable String id, HttpServletRequest request) {
        return ResultUtils.success(feedback.list(id,users.getLoginUser(request)));
    }
}
