package com.yupi.yupicture.interfaces.controller.agent;

import com.yupi.yupicture.application.agent.AgentInternalTaskService;
import com.yupi.yupicture.application.agent.AgentInternalPictureSearchService;
import com.yupi.yupicture.application.agent.AgentInternalPictureDetailsService;
import com.yupi.yupicture.application.agent.AgentInternalPictureVisionService;
import com.yupi.yupicture.application.agent.AgentInternalSpaceAnalyzeService;
import com.yupi.yupicture.infrastructure.common.*;
import com.yupi.yupicture.interfaces.dto.agent.*;
import org.springframework.web.bind.annotation.*;
import javax.annotation.Resource;
import java.util.Map;
import java.util.List;

@RestController
@RequestMapping("/agent/internal/tasks")
public class AgentInternalController {
    @Resource private AgentInternalTaskService internal;
    @Resource private AgentInternalPictureSearchService pictureSearch;
    @Resource private AgentInternalPictureDetailsService pictureDetails;
    @Resource private AgentInternalPictureVisionService pictureVision;
    @Resource private AgentInternalSpaceAnalyzeService spaceAnalyze;

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
    @PostMapping("/{id}/pictures/search")
    public BaseResponse<List<Map<String,Object>>> searchPictures(@PathVariable String id,
            @RequestHeader("Authorization") String authorization,
            @RequestBody AgentInternalSearchRequest body) {
        return ResultUtils.success(pictureSearch.search(authorization,id,body));
    }
    @PostMapping("/{id}/pictures/details")
    public BaseResponse<List<Map<String,Object>>> pictureDetails(@PathVariable String id,
            @RequestHeader("Authorization") String authorization,
            @RequestBody AgentInternalPictureIdsRequest body) {
        return ResultUtils.success(pictureDetails.details(authorization,id,
                body == null ? null : body.getPictureIds()));
    }
    @PostMapping("/{id}/pictures/vision-inputs")
    public BaseResponse<List<Map<String,Object>>> pictureVisionInputs(@PathVariable String id,
            @RequestHeader("Authorization") String authorization,
            @RequestBody AgentInternalPictureIdsRequest body) {
        return ResultUtils.success(pictureVision.inputs(authorization,id,
                body == null ? null : body.getPictureIds()));
    }

    @GetMapping("/{id}/spaces/compare")
    public BaseResponse<List<Map<String,Object>>> compareSpaces(@PathVariable String id,
            @RequestHeader("Authorization") String authorization) {
        return ResultUtils.success(spaceAnalyze.compare(authorization,id));
    }

    @GetMapping("/{id}/spaces/summary")
    public BaseResponse<Map<String,Object>> spaceSummary(@PathVariable String id,
            @RequestHeader("Authorization") String authorization) {
        return ResultUtils.success(spaceAnalyze.summary(authorization, id));
    }
}
