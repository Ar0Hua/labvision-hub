package com.yupi.yupicture.application.agent;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.yupi.yupicture.domain.picture.entity.Picture;
import com.yupi.yupicture.interfaces.dto.agent.AgentInternalSearchRequest;
import com.yupi.yupicture.infrastructure.exception.*;
import java.util.*;

/** Fixed SQL expressions; user values are always bound parameters. */
public final class AgentVisualSearchFilters {
    private AgentVisualSearchFilters() { }

    public static void validate(AgentInternalSearchRequest request) {
        if (request.getTargetColor() != null && !request.getTargetColor().matches("#[0-9a-fA-F]{6}")) invalid();
        if (request.getColorTolerance() != null && (request.getColorTolerance()<0 || request.getColorTolerance()>255)) invalid();
        if (request.getBrightness() != null && !Arrays.asList("dark", "normal", "bright").contains(request.getBrightness())) invalid();
    }

    public static void apply(QueryWrapper<Picture> query, AgentInternalSearchRequest request) {
        validate(request);
        if (request.getTargetColor() != null) {
            int tolerance=request.getColorTolerance()==null?48:request.getColorTolerance();
            String normalized="REPLACE(REPLACE(LOWER(TRIM(picColor)), '0x', ''), '#', '')";
            query.apply(normalized + " REGEXP '^[0-9a-f]{6}$'");
            for (int i=0;i<3;i++) {
                int channel=Integer.parseInt(request.getTargetColor().substring(1+i*2,3+i*2),16);
                query.apply("CONV(SUBSTRING("+normalized+", "+(1+i*2)+", 2),16,10)+0 BETWEEN {0} AND {1}",
                        Math.max(0,channel-tolerance),Math.min(255,channel+tolerance));
            }
        }
        if (request.getBrightness() != null) {
            String condition="dark".equals(request.getBrightness())?"f.brightnessScore < 50":
                    "bright".equals(request.getBrightness())?"f.brightnessScore > 210":"f.brightnessScore BETWEEN 50 AND 210";
            // A current READY feature is required. Outer query still restricts authorized scope.
            query.inSql("id", "SELECT f.pictureId FROM picture_ai_feature f JOIN picture p ON p.id=f.pictureId"
                    + " WHERE f.indexStatus='READY' AND p.isDelete=0"
                    + " AND UNIX_TIMESTAMP(f.sourceUpdatedAt)=FLOOR(UNIX_TIMESTAMP(COALESCE(p.updateTime,p.editTime,p.createTime)))"
                    + " AND " + condition);
        }
    }

    private static void invalid() { throw new BusinessException(ErrorCode.PARAMS_ERROR,"非法颜色或亮度条件"); }
}
