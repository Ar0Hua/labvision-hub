package com.yupi.yupicture.application.agent;

import cn.hutool.core.util.StrUtil;
import com.yupi.yupicture.domain.picture.entity.Picture;
import com.yupi.yupicture.domain.picture.repository.PictureRepository;
import com.yupi.yupicture.domain.user.entity.User;
import com.yupi.yupicture.infrastructure.api.CosManager;
import com.yupi.yupicture.infrastructure.exception.BusinessException;
import com.yupi.yupicture.infrastructure.exception.ErrorCode;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import javax.annotation.Resource;
import java.util.*;

/** 权限校验完成后，按需签发视觉模型专用的短期缩略图地址。 */
@Service
public class AgentInternalPictureVisionService {
    private static final int MAX_VISION_PICTURES = 8;
    private static final int URL_TTL_SECONDS = 120;

    @Resource private AgentInternalTaskService internalTasks;
    @Resource private AgentPictureService authorizedPictures;
    @Resource private PictureRepository pictures;
    @Resource private CosManager cos;

    @Transactional(readOnly = true)
    public List<Map<String, Object>> inputs(String bearerToken, String taskId, List<Long> pictureIds) {
        if (pictureIds == null || pictureIds.isEmpty() || pictureIds.size() > MAX_VISION_PICTURES) {
            throw new BusinessException(ErrorCode.PARAMS_ERROR, "视觉分析请选择 1 至 8 张图片");
        }
        Map<String, Object> context = internalTasks.context(bearerToken, taskId);
        User user = new User();
        user.setId(Long.valueOf(context.get("userId").toString()));
        user.setUserRole((String)context.get("userRole"));
        return previews(context.get("conversationId").toString(),pictureIds,user);
    }

    @Transactional(readOnly = true)
    public List<Map<String,Object>> previews(String conversationId,List<Long> pictureIds,User user) {
        if(pictureIds==null || pictureIds.isEmpty() || pictureIds.size()>MAX_VISION_PICTURES)
            throw new BusinessException(ErrorCode.PARAMS_ERROR,"请选择1至8张图片");
        List<Map<String, Object>> metadata = authorizedPictures.details(conversationId, pictureIds, user);
        List<Map<String, Object>> result = new ArrayList<>();
        for (Map<String, Object> item : metadata) {
            Long pictureId = Long.valueOf(item.get("pictureId").toString());
            Picture picture = pictures.getById(pictureId);
            if (picture == null || !Integer.valueOf(0).equals(picture.getIsDelete())) {
                throw new BusinessException(ErrorCode.NO_AUTH_ERROR, "图片不可访问");
            }
            String source = StrUtil.isNotBlank(picture.getThumbnailUrl())
                    ? picture.getThumbnailUrl() : picture.getUrl();
            if (StrUtil.isBlank(source)) {
                throw new BusinessException(ErrorCode.OPERATION_ERROR, "图片没有可分析的对象地址");
            }
            Map<String, Object> vision = new LinkedHashMap<>(item);
            try {
                vision.put("temporaryUrl", cos.generatePresignedGetUrl(source, URL_TTL_SECONDS));
            } catch (IllegalArgumentException exception) {
                throw new BusinessException(ErrorCode.OPERATION_ERROR, "图片临时访问地址生成失败");
            }
            vision.put("expiresInSeconds", URL_TTL_SECONDS);
            result.add(vision);
        }
        return result;
    }
}
