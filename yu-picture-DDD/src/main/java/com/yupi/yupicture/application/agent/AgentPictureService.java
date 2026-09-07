package com.yupi.yupicture.application.agent;

import com.yupi.yupicture.domain.picture.entity.Picture;
import com.yupi.yupicture.domain.picture.repository.PictureRepository;
import com.yupi.yupicture.domain.user.entity.User;
import com.yupi.yupicture.infrastructure.exception.BusinessException;
import com.yupi.yupicture.infrastructure.exception.ErrorCode;
import org.springframework.stereotype.Service;
import javax.annotation.Resource;
import java.util.*;

/** 仅返回已授权图片的元数据，不下发永久 COS URL 或原始实体。 */
@Service
public class AgentPictureService {
    @Resource private AgentConversationService conversations;
    @Resource private AgentAccessService access;
    @Resource private PictureRepository pictures;

    public List<Map<String, Object>> details(String conversationId, List<Long> ids, User user) {
        conversations.requireOwner(conversationId, user);
        if (ids == null || ids.isEmpty() || ids.size() > 20) {
            throw new BusinessException(ErrorCode.PARAMS_ERROR, "请选择 1 至 20 张图片");
        }
        List<Map<String, Object>> result = new ArrayList<>();
        for (Long id : new LinkedHashSet<>(ids)) {
            if (id == null || id <= 0) {
                throw new BusinessException(ErrorCode.PARAMS_ERROR, "图片 ID 必须为正整数");
            }
            Picture picture = pictures.getById(id);
            if (picture == null || !Integer.valueOf(0).equals(picture.getIsDelete())) {
                deny();
            }
            conversations.requirePictureScope(conversationId, user, picture.getSpaceId());
            if (picture.getSpaceId() != null) {
                access.resolve(user, Collections.singletonList(picture.getSpaceId()));
            } else if (!Integer.valueOf(1).equals(picture.getReviewStatus())) {
                deny();
            }
            Map<String, Object> item = new LinkedHashMap<>();
            item.put("pictureId", id.toString());
            item.put("spaceId", picture.getSpaceId() == null ? null : picture.getSpaceId().toString());
            item.put("name", picture.getName());
            item.put("introduction", picture.getIntroduction());
            item.put("category", picture.getCategory());
            item.put("tags", picture.getTags());
            item.put("width", picture.getPicWidth());
            item.put("height", picture.getPicHeight());
            item.put("size", picture.getPicSize());
            item.put("format", picture.getPicFormat());
            result.add(item);
        }
        return result;
    }

    private void deny() {
        throw new BusinessException(ErrorCode.NO_AUTH_ERROR, "图片不可访问");
    }
}
