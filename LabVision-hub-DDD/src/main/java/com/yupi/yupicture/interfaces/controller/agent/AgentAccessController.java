package com.yupi.yupicture.interfaces.controller.agent;

import com.yupi.yupicture.application.agent.AgentAccessService;
import com.yupi.yupicture.application.service.UserApplicationService;
import com.yupi.yupicture.infrastructure.common.BaseResponse;
import com.yupi.yupicture.infrastructure.common.ResultUtils;
import org.springframework.web.bind.annotation.*;
import javax.annotation.Resource;
import javax.servlet.http.HttpServletRequest;
import java.util.*;

@RestController
@RequestMapping("/agent")
public class AgentAccessController {
    @Resource
    private UserApplicationService userService;
    @Resource
    private AgentAccessService accessService;

    /** 空列表仅表示公共图库；客户端不能指定授权用户。 */
    @PostMapping("/access-scope")
    public BaseResponse<Map<String, Object>> resolve(
            @RequestBody List<Long> spaceIds, HttpServletRequest request) {
        return ResultUtils.success(accessService.resolve(userService.getLoginUser(request), spaceIds));
    }
}
