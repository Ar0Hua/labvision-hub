package com.yupi.yupicture.interfaces.controller.agent;

import com.yupi.yupicture.application.agent.AgentConversationService;
import com.yupi.yupicture.application.agent.AgentPictureService;
import com.yupi.yupicture.application.agent.AgentMessageService;
import com.yupi.yupicture.domain.agent.AgentMessage;
import com.yupi.yupicture.interfaces.dto.agent.AgentConversationCreateRequest;
import com.yupi.yupicture.interfaces.dto.agent.AgentMessageCreateRequest;
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
    @Resource private AgentMessageService messages;

    @PostMapping
    public BaseResponse<Map<String, String>> create(
            @RequestBody(required = false) AgentConversationCreateRequest body, HttpServletRequest request) {
        return ResultUtils.success(Collections.singletonMap("conversationId",
                conversations.create(users.getLoginUser(request), body == null ? null : body.getSpaceId())));
    }

    @PostMapping("/{id}/pictures/details")
    public BaseResponse<List<Map<String, Object>>> details(@PathVariable String id,
            @RequestBody List<Long> pictureIds, HttpServletRequest request) {
        return ResultUtils.success(pictures.details(id, pictureIds, users.getLoginUser(request)));
    }
    @PostMapping("/{id}/messages")
    public BaseResponse<AgentMessage> createMessage(@PathVariable String id,@RequestBody AgentMessageCreateRequest body,HttpServletRequest request) {
        return ResultUtils.success(messages.createUserMessage(id,body==null?null:body.getContent(),users.getLoginUser(request)));
    }
    @GetMapping("/{id}/messages")
    public BaseResponse<List<AgentMessage>> listMessages(@PathVariable String id,HttpServletRequest request) {
        return ResultUtils.success(messages.list(id,users.getLoginUser(request)));
    }
}
