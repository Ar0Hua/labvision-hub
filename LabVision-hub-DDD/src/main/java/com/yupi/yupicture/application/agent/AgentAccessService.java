package com.yupi.yupicture.application.agent;

import com.yupi.yupicture.domain.space.entity.Space;
import com.yupi.yupicture.domain.space.repository.SpaceRepository;
import com.yupi.yupicture.domain.user.entity.User;
import com.yupi.yupicture.infrastructure.exception.BusinessException;
import com.yupi.yupicture.infrastructure.exception.ErrorCode;
import com.yupi.yupicture.shared.auth.SpaceUserAuthManager;
import com.yupi.yupicture.shared.auth.model.SpaceUserPermissionConstant;
import org.springframework.stereotype.Service;
import javax.annotation.Resource;
import java.util.*;

/** 每次请求重新验证指定空间；此结果不是可用于服务间调用的授权令牌。 */
@Service
public class AgentAccessService {
    @Resource
    private SpaceRepository spaceRepository;
    @Resource
    private SpaceUserAuthManager authManager;
    @Resource private com.yupi.yupicture.infrastructure.mapper.AgentScopeCandidatesMapper scopeCandidates;

    public List<Long> allViewableSpaceIds(User user) {
        if (user==null || user.getId()==null) throw new BusinessException(ErrorCode.NOT_LOGIN_ERROR);
        List<Long> candidates=scopeCandidates.candidates(user.getId(),user.isAdmin());
        if (candidates.size()>500) throw new BusinessException(ErrorCode.PARAMS_ERROR,"空间数量超出全范围查询上限，请选择具体空间");
        List<Long> result=new ArrayList<>();
        for (Long id:candidates) {
            Space space=spaceRepository.getById(id);
            if(space==null) continue;
            List<String> granted=authManager.getPermissionList(space,user);
            if(granted!=null && granted.contains(SpaceUserPermissionConstant.PICTURE_VIEW)) result.add(id);
        }
        if(result.size()>50) throw new BusinessException(ErrorCode.PARAMS_ERROR,"全范围会话最多支持50个授权空间，请选择具体空间");
        return result;
    }

    public Map<String, Object> resolve(User user, List<Long> spaceIds) {
        if (user == null || user.getId() == null) {
            throw new BusinessException(ErrorCode.NOT_LOGIN_ERROR);
        }
        if (spaceIds == null || spaceIds.size() > 50) {
            throw new BusinessException(ErrorCode.PARAMS_ERROR, "最多指定 50 个空间");
        }
        Map<String, List<String>> permissions = new LinkedHashMap<>();
        for (Long id : new LinkedHashSet<>(spaceIds)) {
            if (id == null || id <= 0) {
                throw new BusinessException(ErrorCode.PARAMS_ERROR, "空间 ID 必须为正整数");
            }
            Space space = spaceRepository.getById(id);
            // 不向无权用户区分空间不存在和空间无权限。
            if (space == null) {
                throw new BusinessException(ErrorCode.NO_AUTH_ERROR, "无法访问指定空间");
            }
            List<String> granted = authManager.getPermissionList(space, user);
            if (granted == null || !granted.contains(SpaceUserPermissionConstant.PICTURE_VIEW)) {
                throw new BusinessException(ErrorCode.NO_AUTH_ERROR, "无法访问指定空间");
            }
            permissions.put(id.toString(), new ArrayList<>(granted));
        }
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("userId", user.getId().toString());
        result.put("permissionsBySpace", permissions);
        result.put("allowedSpaceIds", new ArrayList<>(permissions.keySet()));
        // 公共图不能以虚构的空间 0 代替：实际数据中 spaceId 为 null。
        result.put("includeApprovedPublic", true);
        result.put("requiresResourceRecheck", true);
        return result;
    }
}
