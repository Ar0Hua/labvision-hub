from dataclasses import dataclass
import json
from typing import Protocol

from app.config import Settings
from app.runtime.java_client import JavaTaskClient, TaskContext
from app.retrieval.keyword_executor import (
    AuthorizePictures, CheckActive, ExecutionResult, KeywordSearchExecutor, SearchPictures,
)
from app.retrieval.intent import IntentParser
from app.retrieval.semantic import SemanticRetriever
from app.security.service_token import ServiceContext
from app.graph.workflow import RedisCheckpointWorkflow


class ExecutorUnavailable(RuntimeError):
    pass


class TaskCancelled(RuntimeError):
    pass


class TaskExecutor(Protocol):
    def execute(
        self, context: TaskContext, search: SearchPictures, authorize: AuthorizePictures,
        check_active: CheckActive,
    ) -> ExecutionResult:
        ...


class DisabledExecutor:
    def execute(
        self, context: TaskContext, search: SearchPictures, authorize: AuthorizePictures,
        check_active: CheckActive,
    ) -> ExecutionResult:
        raise ExecutorUnavailable("retrieval executor is not configured")


@dataclass
class TaskRunner:
    java: JavaTaskClient
    executor: TaskExecutor

    @classmethod
    def from_settings(cls, settings: Settings) -> "TaskRunner":
        executor = KeywordSearchExecutor(IntentParser(settings), SemanticRetriever(settings))
        return cls(
            JavaTaskClient(settings),
            RedisCheckpointWorkflow(executor, settings),
        )

    def run(self, signed: ServiceContext, token: str) -> None:
        running = False
        try:
            context = self.java.get_context(signed.task_id, token)
            self._assert_scope(context, signed)
            if context.status == "CANCELLED":
                return
            if context.status != "PENDING":
                raise ValueError("task is not pending")
            self.java.update_state(
                signed.task_id, token, status="RUNNING", stage="INITIALIZING"
            )
            running = True
            self.java.append_event(
                signed.task_id, token, "tool_start",
                json.dumps({"tool": "picture_keyword_search"}, separators=(",", ":")),
            )
            result = self.executor.execute(
                context,
                lambda text, category, tags, limit: self.java.search_pictures(
                    signed.task_id, token, search_text=text, category=category, tags=tags, limit=limit
                ),
                lambda ids: self.java.authorize_pictures(signed.task_id, token, ids),
                lambda: self._ensure_active(signed, token),
            )
            self._ensure_active(signed, token)
            self.java.append_event(
                signed.task_id, token, "tool_result",
                json.dumps({"tool": "picture_keyword_search", "count": result.candidate_count},
                           separators=(",", ":")),
            )
            for citation in result.citations:
                self.java.append_event(
                    signed.task_id, token, "citation",
                    json.dumps(citation, ensure_ascii=False, separators=(",", ":")),
                )
            self.java.append_event(
                signed.task_id,
                token,
                "answer_delta",
                json.dumps({"text": result.answer}, ensure_ascii=False, separators=(",", ":")),
            )
            self.java.update_state(
                signed.task_id, token, status="SUCCEEDED", stage="COMPLETED"
            )
        except TaskCancelled:
            pass
        except ExecutorUnavailable:
            if running:
                self._try_fail(
                    signed.task_id,
                    token,
                    status="FAILED",
                    stage="EXECUTOR_UNAVAILABLE",
                    error_code="EXECUTOR_UNAVAILABLE",
                    error_message="Agent 检索执行器尚未配置",
                )
        except Exception:
            if running:
                self._try_fail(
                    signed.task_id,
                    token,
                    status="FAILED",
                    stage="INTERNAL_ERROR",
                    error_code="AGENT_INTERNAL_ERROR",
                    error_message="Agent 执行失败，请稍后重试",
                )
        finally:
            self.java.close()

    def _ensure_active(self, signed: ServiceContext, token: str) -> None:
        context = self.java.get_context(signed.task_id, token)
        self._assert_scope(context, signed)
        if context.status == "CANCELLED":
            raise TaskCancelled()
        if context.status != "RUNNING":
            raise ValueError("task is no longer running")

    def _try_fail(self, task_id: str, token: str, **kwargs) -> None:
        try:
            self.java.update_state(task_id, token, **kwargs)
        except Exception:
            pass

    @staticmethod
    def _assert_scope(context: TaskContext, signed: ServiceContext) -> None:
        if (
            context.taskId != signed.task_id
            or context.conversationId != signed.conversation_id
            or context.userId != signed.user_id
            or context.spaceId != signed.space_id
        ):
            raise ValueError("Java context does not match signed scope")
