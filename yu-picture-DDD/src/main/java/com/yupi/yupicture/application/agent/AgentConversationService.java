package com.yupi.yupicture.application.agent;

import com.yupi.yupicture.domain.user.entity.User;
import com.yupi.yupicture.infrastructure.exception.BusinessException;
import com.yupi.yupicture.infrastructure.exception.ErrorCode;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;
import javax.annotation.Resource;
import java.time.Duration;
import java.util.UUID;

/** Redis 保存短期会话归属，后续持久消息和审计使用 MySQL。 */
@Service
public class AgentConversationService {
    private static final String PREFIX = "labvision:agent:conversation:owner:";
    @Resource
    private StringRedisTemplate redis;

    public String create(User user) {
        requireUser(user);
        String id = UUID.randomUUID().toString();
        redis.opsForValue().set(PREFIX + id, user.getId().toString(), Duration.ofHours(24));
        return id;
    }

    public void requireOwner(String id, User user) {
        requireUser(user);
        if (id == null || !id.matches("[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")) {
            throw new BusinessException(ErrorCode.NO_AUTH_ERROR, "会话不可访问或已过期");
        }
        String owner = redis.opsForValue().get(PREFIX + id);
        if (!user.getId().toString().equals(owner)) {
            throw new BusinessException(ErrorCode.NO_AUTH_ERROR, "会话不可访问或已过期");
        }
    }

    private void requireUser(User user) {
        if (user == null || user.getId() == null) {
            throw new BusinessException(ErrorCode.NOT_LOGIN_ERROR);
        }
    }
}
