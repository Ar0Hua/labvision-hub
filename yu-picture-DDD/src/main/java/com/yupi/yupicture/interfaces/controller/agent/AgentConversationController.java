package com.yupi.yupicture.interfaces.controller.agent;

import com.yupi.yupicture.application.agent.AgentConversationService;
import com.yupi.yupicture.application.agent.AgentPictureService;
import com.yupi.yupicture.application.service.UserApplicationService;
import com.yupi.yupicture.infrastructure.common.BaseResponse;
import com.yupi.yupicture.infrastructure.common.ResultUtils;
import org.springframework.web.bind.annotation.*;
import javax.annotation.Resource;
import javax.servlet.http.HttpServletRequest;
import java.util.*;

@RestController
@RequestMapping("/agent/conversations")
public class AgentConversationController {
    @Resource private UserApplicationService users;
    @Resource private AgentConversationService conversations;
    @Resource private AgentPictureService pictures;

    @PostMapping
    public BaseResponse<Map<String, String>> create(HttpServletRequest request) {
        return ResultUtils.success(Collections.singletonMap("conversationId",
                conversations.create(users.getLoginUser(request))));
    }

    @PostMapping("/{id}/pictures/details")
    public BaseResponse<List<Map<String, Object>>> details(@PathVariable String id,
            @RequestBody List<Long> pictureIds, HttpServletRequest request) {
        return ResultUtils.success(pictures.details(id, pictureIds, users.getLoginUser(request)));
    }
}
