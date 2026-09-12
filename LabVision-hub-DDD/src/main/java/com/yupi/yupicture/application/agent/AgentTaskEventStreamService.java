package com.yupi.yupicture.application.agent;

import com.yupi.yupicture.domain.user.entity.User;
import com.yupi.yupicture.infrastructure.exception.BusinessException;
import com.yupi.yupicture.infrastructure.exception.ErrorCode;
import com.yupi.yupicture.interfaces.vo.agent.*;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;
import javax.annotation.Resource;
import java.io.IOException;
import java.util.List;

@Service
public class AgentTaskEventStreamService {
    private static final long POLL_MILLIS = 500L;
    private static final long STREAM_MILLIS = 25_000L;
    @Resource private AgentTaskEventService events;
    @Resource private AgentTaskService tasks;

    /** 在返回 SSE 响应前同步校验权限和游标。 */
    public void authorize(String taskId, long cursor, User user) {
        events.listAfter(taskId, cursor, 1, user);
    }

    @Async
    public void stream(SseEmitter emitter, String taskId, long cursor, User user) {
        long current = cursor;
        long deadline = System.currentTimeMillis() + STREAM_MILLIS;
        try {
            while (System.currentTimeMillis() < deadline) {
                List<AgentTaskEventVO> batch = events.listAfter(taskId, current, 100, user);
                for (AgentTaskEventVO event : batch) {
                    emitter.send(SseEmitter.event()
                            .id(event.getEventId())
                            .name(event.getEventType())
                            .reconnectTime(1000)
                            .data(event.getPayloadJson()));
                    current = Long.parseLong(event.getEventId());
                }
                AgentTaskVO task = tasks.get(taskId, user);
                if (batch.isEmpty() && isTerminal(task.getStatus())) {
                    break;
                }
                Thread.sleep(POLL_MILLIS);
            }
            emitter.complete();
        } catch (IOException | IllegalStateException ignored) {
            // 客户端断开时结束该流；持久事件可通过 Last-Event-ID 恢复。
            emitter.complete();
        } catch (InterruptedException interrupted) {
            Thread.currentThread().interrupt();
            emitter.complete();
        } catch (RuntimeException error) {
            emitter.completeWithError(error);
        }
    }

    public long parseCursor(String lastEventId, Long queryCursor) {
        String value = lastEventId == null || lastEventId.trim().isEmpty()
                ? (queryCursor == null ? "0" : queryCursor.toString())
                : lastEventId.trim();
        try {
            long cursor = Long.parseLong(value);
            if (cursor < 0) throw new NumberFormatException();
            return cursor;
        } catch (NumberFormatException error) {
            throw new BusinessException(ErrorCode.PARAMS_ERROR, "Last-Event-ID 非法");
        }
    }

    private boolean isTerminal(String status) {
        return "SUCCEEDED".equals(status) || "FAILED".equals(status) || "CANCELLED".equals(status);
    }
}
