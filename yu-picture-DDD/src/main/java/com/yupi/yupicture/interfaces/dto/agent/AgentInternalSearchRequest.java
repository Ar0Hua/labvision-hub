package com.yupi.yupicture.interfaces.dto.agent;

import lombok.Data;
import java.util.List;

@Data
public class AgentInternalSearchRequest {
    private String searchText;
    private String category;
    private List<String> tags;
    private Integer limit;
    private List<String> formats;
    private String createdAfter;
    private String createdBefore;
    private Integer minWidth;
    private Integer minHeight;
    private Long maxSizeBytes;
    private String sort;
}
