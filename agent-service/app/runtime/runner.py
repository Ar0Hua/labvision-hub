from dataclasses import dataclass
import json
import time
from typing import Protocol

from app.config import Settings
from app.runtime.java_client import JavaTaskClient, PictureCandidate, TaskContext
from app.retrieval.keyword_executor import (
    AuthorizePictures, CheckActive, ExecutionResult, KeywordSearchExecutor, SearchPictures,
)
from app.retrieval.intent import IntentParser
from app.retrieval.semantic import SemanticRetriever
from app.analysis.space_statistics import SpaceStatisticsComposer
from app.analysis.group_analysis import PictureGroupAnalyzer
from app.security.service_token import ServiceContext
from app.graph.workflow import RedisCheckpointWorkflow
from app.analysis.vision import VisionAnalyzer
from app.observability.metrics import runtime_metrics


class ExecutorUnavailable(RuntimeError):
    pass


class TaskCancelled(RuntimeError):
    pass


class TaskDeadlineExceeded(RuntimeError):
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
    vision: VisionAnalyzer | None = None
    timeout_seconds: float = 120
    semantic: SemanticRetriever | None = None

    @classmethod
    def from_settings(cls, settings: Settings) -> "TaskRunner":
        semantic = SemanticRetriever(settings)
        executor = KeywordSearchExecutor(IntentParser(settings), semantic)
        return cls(
            JavaTaskClient(settings),
            RedisCheckpointWorkflow(executor, settings),
            VisionAnalyzer(settings),
            settings.task_timeout_seconds,
            semantic,
        )

    def run(self, signed: ServiceContext, token: str) -> None:
        running = False
        started = time.monotonic()
        outcome = "ignored"
        empty_result = False
        deadline = started + self.timeout_seconds
        def check_active() -> None:
            if time.monotonic() >= deadline:
                raise TaskDeadlineExceeded()
            self._ensure_active(signed, token)
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
            is_group_analysis = PictureGroupAnalyzer.matches(
                context.query, context.examplePictureIds)
            is_single_analysis = (
                len(context.examplePictureIds) == 1
                and any(word in context.query for word in ("分析", "解释", "描述", "质量", "文字"))
                and not any(word in context.query for word in ("查找", "搜索", "找相似", "检索")))
            is_space_statistics = (
                not is_single_analysis and not is_group_analysis and SpaceStatisticsComposer.matches(context.query))
            tool_name = (
                "picture_analysis" if is_single_analysis else
                "picture_group_analysis" if is_group_analysis else
                ("space_statistics" if is_space_statistics else "picture_keyword_search")
            )
            self.java.append_event(
                signed.task_id, token, "tool_start",
                json.dumps({"tool": tool_name}, separators=(",", ":")),
            )
            if is_single_analysis:
                selected = self.java.authorize_pictures(
                    signed.task_id, token, context.examplePictureIds)
                if len(selected) != 1 or selected[0].pictureId != context.examplePictureIds[0]:
                    raise ValueError("selected picture is unavailable")
                picture = selected[0]
                facts = [
                    f"选中图片：[图片 ID: {picture.pictureId}]",
                    f"- 名称：{picture.name or '未命名'}",
                    f"- 分类：{picture.category or '未分类'}",
                    f"- 格式：{picture.format or '未知'}",
                    f"- 分辨率：{picture.width or '未知'} × {picture.height or '未知'}",
                    f"- 大小：{picture.size if picture.size is not None else '未知'} 字节",
                    f"- 标签：{picture.tags or '无'}",
                    "以上来自当前权限范围内的图片元数据。",
                ]
                result = ExecutionResult("\n".join(facts), [{
                    "pictureId": picture.pictureId, "name": picture.name,
                    "category": picture.category,
                }], 1)
                tool_result = {"tool": tool_name, "count": 1}
            elif is_group_analysis:
                selected = self.java.authorize_pictures(
                    signed.task_id, token, context.examplePictureIds)
                group = PictureGroupAnalyzer.analyze(selected)
                result = ExecutionResult(
                    group.answer, group.citations, group.picture_count)
                tool_result = {
                    "tool": tool_name,
                    "count": group.picture_count,
                }
            elif is_space_statistics:
                summary = self.java.get_space_statistics(signed.task_id, token)
                result = ExecutionResult(
                    SpaceStatisticsComposer.compose(summary), [], 0)
                tool_result = {
                    "tool": tool_name,
                    "scopeType": summary.scope.type,
                    "capturedAt": summary.capturedAt.isoformat(),
                }
            else:
                result = self.executor.execute(
                    context,
                    lambda text, category, tags, limit, filters: self.java.search_pictures(
                        signed.task_id, token, search_text=text, category=category, tags=tags,
                        limit=limit, filters=filters),
                    lambda ids: self.java.authorize_pictures(signed.task_id, token, ids),
                    check_active,
                )
                empty_result = result.candidate_count == 0
                tool_result = {"tool": tool_name, "count": result.candidate_count}
            check_active()
            self.java.append_event(
                signed.task_id, token, "tool_result",
                json.dumps(tool_result, separators=(",", ":")),
            )
            if is_group_analysis:
                result = self._add_group_similarity(
                    result, selected, context, signed, token, check_active)
            for citation in result.citations:
                self.java.append_event(
                    signed.task_id, token, "citation",
                    json.dumps(citation, ensure_ascii=False, separators=(",", ":")),
                )
            if not is_space_statistics:
                result = self._add_visual_analysis(
                    result, context, signed, token, check_active)
            check_active()
            self.java.append_event(
                signed.task_id,
                token,
                "answer_delta",
                json.dumps({"text": result.answer}, ensure_ascii=False, separators=(",", ":")),
            )
            self.java.update_state(
                signed.task_id, token, status="SUCCEEDED", stage="COMPLETED"
            )
            outcome = "succeeded"
        except TaskCancelled:
            outcome = "cancelled"
        except TaskDeadlineExceeded:
            outcome = "timeout"
            if running:
                self._try_fail(
                    signed.task_id, token, status="FAILED", stage="TIMEOUT",
                    error_code="TASK_TIMEOUT", error_message="Agent 任务超过总执行时间限制",
                )
        except ExecutorUnavailable:
            outcome = "unavailable"
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
            outcome = "failed"
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
            runtime_metrics.observe_task(outcome, time.monotonic() - started, empty_result)
            self.java.close()

    def _add_group_similarity(
        self, result: ExecutionResult, pictures: list[PictureCandidate],
        context: TaskContext, signed: ServiceContext, token: str,
        check_active: CheckActive,
    ) -> ExecutionResult:
        if not self.semantic:
            return result
        picture_ids = [picture.pictureId for picture in pictures]
        self.java.append_event(
            signed.task_id, token, "tool_start",
            json.dumps(
                {"tool": "picture_group_similarity", "count": len(picture_ids)},
                separators=(",", ":"),
            ),
        )
        try:
            scope_key = "public" if context.spaceId is None else "space:" + context.spaceId
            matrix = self.semantic.picture_similarity_matrix(picture_ids, scope_key)
            check_active()
            analysis = PictureGroupAnalyzer.analyze_similarity(pictures, matrix)
        except (TaskCancelled, TaskDeadlineExceeded):
            raise
        except Exception:
            self.java.append_event(
                signed.task_id, token, "tool_result",
                json.dumps(
                    {"tool": "picture_group_similarity", "available": False},
                    separators=(",", ":"),
                ),
            )
            return result
        self.java.append_event(
            signed.task_id, token, "tool_result",
            json.dumps(
                {
                    "tool": "picture_group_similarity",
                    "available": True,
                    "knownPairs": analysis.known_pair_count,
                    "totalPairs": analysis.total_pair_count,
                },
                separators=(",", ":"),
            ),
        )
        return ExecutionResult(
            answer=result.answer + "\n\n" + analysis.answer,
            citations=result.citations,
            candidate_count=result.candidate_count,
            intent_state=result.intent_state,
        )

    def _add_visual_analysis(
        self, result: ExecutionResult, context: TaskContext, signed: ServiceContext, token: str,
        check_active: CheckActive,
    ) -> ExecutionResult:
        if not self.vision or not self.vision.enabled or not result.citations:
            return result
        picture_ids = list(dict.fromkeys(
            item["pictureId"] for item in result.citations if item.get("pictureId")))[:20]
        if not picture_ids:
            return result
        batch_size = max(1, min(8, self.vision.max_pictures))
        observations = []
        covered = 0
        self.java.append_event(
            signed.task_id, token, "tool_start",
            json.dumps({"tool": "vision_analysis", "count": len(picture_ids)}))
        for offset in range(0, len(picture_ids), batch_size):
            check_active()
            batch = picture_ids[offset:offset + batch_size]
            try:
                inputs = self.java.get_vision_inputs(signed.task_id, token, batch)
            except Exception:
                check_active()
                continue
            check_active()
            if any(item.pictureId not in batch for item in inputs):
                raise ValueError("vision inputs exceed authorized batch")
            analysis = self.vision.analyze(context.query, inputs)
            check_active()
            if analysis:
                covered += len({item.pictureId for item in inputs})
                observations.append(f"批次 {offset // batch_size + 1}：\n" + analysis)
        self.java.append_event(
            signed.task_id, token, "tool_result",
            json.dumps({"tool": "vision_analysis", "count": covered,
                        "totalCount": len(picture_ids), "available": bool(observations)}))
        if not observations:
            return result
        return ExecutionResult(
            answer=(result.answer + f"\n\n视觉模型观察（覆盖 {covered}/{len(picture_ids)} 张，"
                    "不代表实验事实）：\n" + "\n\n".join(observations)),
            citations=result.citations,
            candidate_count=result.candidate_count,
            intent_state=result.intent_state,
        )

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
