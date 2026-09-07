package com.yupi.yupicture.application.agent;

import lombok.AllArgsConstructor;
import lombok.Getter;

@Getter
@AllArgsConstructor
public class AgentTaskDispatchRequested {
    private final String taskId;
}
