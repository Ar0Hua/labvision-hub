package com.yupi.yupicture.interfaces.dto.agent;
import lombok.Data;
import java.util.List;
@Data public class AgentMessageCreateRequest {
    private String content;
    private List<Long> examplePictureIds;
    private String temporaryImageId;
}
