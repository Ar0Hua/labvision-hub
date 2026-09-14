package com.yupi.yupicture.interfaces.controller.agent;

import com.yupi.yupicture.application.agent.AgentPictureIndexJobService;
import com.yupi.yupicture.infrastructure.common.*;
import com.yupi.yupicture.interfaces.dto.agent.*;
import org.springframework.web.bind.annotation.*;

import javax.annotation.Resource;
import java.util.*;

@RestController
@RequestMapping("/agent/internal/index/jobs")
public class AgentIndexInternalController {
    @Resource private AgentPictureIndexJobService jobs;
    @Resource private com.yupi.yupicture.application.agent.AgentIndexMaintenanceService maintenance;

    @GetMapping("/maintenance/scan")
    public BaseResponse<List<Map<String,Object>>> scan(@RequestHeader("Authorization") String authorization,
            @RequestParam(defaultValue="0") long after, @RequestParam(defaultValue="100") int limit) {
        return ResultUtils.success(maintenance.scan(authorization,after,limit));
    }

    @PostMapping("/maintenance/enqueue")
    public BaseResponse<Integer> enqueue(@RequestHeader("Authorization") String authorization,
            @RequestParam String runId,@RequestBody List<String> pictureIds) {
        return ResultUtils.success(maintenance.enqueue(authorization,runId,pictureIds));
    }

    @PostMapping("/claim")
    public BaseResponse<List<Map<String,Object>>> claim(
            @RequestHeader("Authorization") String authorization,
            @RequestBody(required = false) AgentIndexClaimRequest request) {
        return ResultUtils.success(jobs.claim(authorization, request == null ? null : request.getLimit()));
    }

    @PostMapping("/{id}/ack")
    public BaseResponse<Boolean> acknowledge(@PathVariable Long id,
            @RequestHeader("Authorization") String authorization,
            @RequestBody AgentIndexAckRequest request) {
        jobs.acknowledge(authorization, id, request);
        return ResultUtils.success(true);
    }
}
