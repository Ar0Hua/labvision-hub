package com.yupi.yupicture.interfaces.controller.agent;

import com.yupi.yupicture.application.agent.AgentConversationService;
import com.yupi.yupicture.application.agent.AgentPictureService;
import com.yupi.yupicture.application.agent.AgentMessageService;
import com.yupi.yupicture.application.agent.AgentTaskService;
import com.yupi.yupicture.domain.agent.AgentMessage;
import com.yupi.yupicture.interfaces.dto.agent.AgentConversationCreateRequest;
import com.yupi.yupicture.interfaces.dto.agent.AgentMessageCreateRequest;
import com.yupi.yupicture.interfaces.vo.agent.AgentTaskVO;
import com.yupi.yupicture.interfaces.vo.agent.AgentConversationVO;
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
    @Resource private AgentTaskService tasks;
    @Resource private com.yupi.yupicture.application.agent.AgentTemporaryImageService temporaryImages;

    @PostMapping("/{id}/temporary-images")
    public BaseResponse<Map<String,Object>> uploadTemporary(@PathVariable String id,
            @RequestParam("file") org.springframework.web.multipart.MultipartFile file,HttpServletRequest request) {
        return ResultUtils.success(temporaryImages.upload(id,users.getLoginUser(request),file));
    }
    @DeleteMapping("/{id}/temporary-images/{temporaryId}")
    public BaseResponse<Boolean> deleteTemporary(@PathVariable String id,@PathVariable String temporaryId,HttpServletRequest request) {
        temporaryImages.remove(id,users.getLoginUser(request),temporaryId);
        return ResultUtils.success(true);
    }

    @PostMapping
    public BaseResponse<Map<String, String>> create(
            @RequestBody(required = false) AgentConversationCreateRequest body, HttpServletRequest request) {
        return ResultUtils.success(Collections.singletonMap("conversationId",
                conversations.create(users.getLoginUser(request), body == null ? null : body.getSpaceId(),
                        body != null && Boolean.TRUE.equals(body.getAllSpaces()))));
    }

    @GetMapping
    public BaseResponse<List<AgentConversationVO>> list(HttpServletRequest request) {
        return ResultUtils.success(conversations.list(users.getLoginUser(request)));
    }

    @PostMapping("/{id}/pictures/details")
    public BaseResponse<List<Map<String, Object>>> details(@PathVariable String id,
            @RequestBody List<Long> pictureIds, HttpServletRequest request) {
        return ResultUtils.success(pictures.details(id, pictureIds, users.getLoginUser(request)));
    }
    @PostMapping("/{id}/messages")
    public BaseResponse<AgentTaskVO> createMessage(@PathVariable String id,@RequestBody AgentMessageCreateRequest body,HttpServletRequest request) {
        return ResultUtils.success(tasks.submit(id,body==null?null:body.getContent(),
                body==null?null:body.getExamplePictureIds(),body==null?null:body.getTemporaryImageId(),users.getLoginUser(request)));
    }
    @GetMapping("/{id}/messages")
    public BaseResponse<List<AgentMessage>> listMessages(@PathVariable String id,HttpServletRequest request) {
        return ResultUtils.success(messages.list(id,users.getLoginUser(request)));
    }
    @GetMapping("/{id}/tasks")
    public BaseResponse<List<AgentTaskVO>> listTasks(@PathVariable String id,HttpServletRequest request) {
        return ResultUtils.success(tasks.listByConversation(id,users.getLoginUser(request)));
    }
}
