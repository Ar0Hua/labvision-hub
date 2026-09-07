package com.yupi.yupicture.interfaces.dto.agent;

import lombok.Data;
import java.util.List;

@Data
public class AgentInternalPictureIdsRequest {
    private List<Long> pictureIds;
}
