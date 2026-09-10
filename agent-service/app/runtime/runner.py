from dataclasses import dataclass
import json
import time
from typing import Protocol

from app.config import Settings
from app.runtime.budget import TaskBudget, BudgetExceeded, active_budget
from app.runtime.model_usage import ModelUsageBudget
from app.runtime.java_client import JavaTaskClient, PictureCandidate, TaskContext
from app.retrieval.keyword_executor import (
    AuthorizePictures, CheckActive, ExecutionResult, KeywordSearchExecutor, SearchPictures,
)
from app.retrieval.intent import IntentParser
from app.retrieval.semantic import SemanticRetriever
from app.analysis.space_statistics import SpaceStatisticsComposer
from app.analysis.group_analysis import PictureGroupAnalyzer
from app.analysis.quality import summarize_features
from app.security.service_token import ServiceContext
from app.graph.workflow import RedisCheckpointWorkflow
from app.analysis.vision import VisionAnalyzer
from app.observability.metrics import runtime_metrics
from app.observability.tracing import traced, set_outcome


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
    max_tool_calls: int = 100
    max_model_calls: int = 10
    max_output_tokens: int = 8000
    max_input_tokens: int = 262144
    max_task_cost: str = "0"
    model_prices_json: str = "{}"
    image_token_reservation: int = 8192

    @classmethod
    def from_settings(cls, settings: Settings) -> "TaskRunner":
        ModelUsageBudget.configured(settings.max_input_tokens, settings.max_task_cost,
                                    settings.model_prices_json, settings.image_token_reservation)
        semantic = SemanticRetriever(settings)
        executor = KeywordSearchExecutor(IntentParser(settings), semantic)
        return cls(
            JavaTaskClient(settings),
            RedisCheckpointWorkflow(executor, settings),
            VisionAnalyzer(settings),
            settings.task_timeout_seconds,
            semantic,
            settings.max_tool_calls, settings.max_model_calls, settings.max_output_tokens,
            settings.max_input_tokens, settings.max_task_cost, settings.model_prices_json, settings.image_token_reservation,
        )

    @traced("agent.task")
    def run(self, signed: ServiceContext, token: str) -> None:
        budget = TaskBudget(self.max_tool_calls, self.max_model_calls, self.max_output_tokens)
        budget.usage = ModelUsageBudget.configured(self.max_input_tokens,self.max_task_cost,
                                                 self.model_prices_json,self.image_token_reservation)
        budget_token = active_budget.set(budget)
        running = False
        started = time.monotonic()
        outcome = "ignored"
        empty_result = False
        published_answer = ""
        phase = "INITIALIZING"
        usage_written = False
        deadline = started + self.timeout_seconds
        def check_active() -> None:
            budget.check()
            if time.monotonic() >= deadline:
                raise TaskDeadlineExceeded()
            self._ensure_active(signed, token)
        def publish(answer: str) -> None:
            nonlocal published_answer
            if not answer.startswith(published_answer):
                raise ValueError("answer enrichment must only append evidence")
            remaining = answer[len(published_answer):]
            for offset in range(0, len(remaining), 2048):
                check_active()
                delta = remaining[offset:offset + 2048]
                self.java.append_event(signed.task_id, token, "answer_delta",
                    json.dumps({"text": delta}, ensure_ascii=False, separators=(",", ":")))
                if not published_answer:
                    runtime_metrics.observe_operation('agent.first_answer', time.monotonic()-started)
                published_answer += delta
        def failure_message(message: str) -> str:
            return (message + f"；失败阶段：{phase}。"
                    + ("已保留此前完成的回答和引用；重试将重新校验权限。" if published_answer else "尚无可展示成果。"))
        def publish_usage():
            nonlocal usage_written
            if usage_written or not budget.models:
                return
            try:
                self.java.append_event(signed.task_id, token, "tool_result",
                    json.dumps({"tool":"model_usage","usage":budget.usage.snapshot()},separators=(",", ":")))
                usage_written = True
            except Exception:
                pass  # A lost/revoked task may not accept further audit writes.
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
            if context.temporaryImageId:
                phase = "TEMPORARY_INPUT"
                check_active()
                context.temporaryImage = self.java.get_temporary_image(signed.task_id, token)
                if context.temporaryImage.temporaryId != context.temporaryImageId:
                    raise ValueError("temporary image binding mismatch")
            is_temporary_analysis = bool(context.temporaryImage and
                any(word in context.query for word in ("分析", "解释", "描述", "质量", "文字")) and
                not any(word in context.query for word in ("查找", "搜索", "找相似", "检索")))
            is_space_comparison = "比较空间" in context.query
            is_group_analysis = not is_space_comparison and PictureGroupAnalyzer.matches(
                context.query, context.examplePictureIds)
            is_single_analysis = (
                len(context.examplePictureIds) == 1
                and any(word in context.query for word in ("分析", "解释", "描述", "质量", "文字"))
                and not any(word in context.query for word in ("查找", "搜索", "找相似", "检索")))
            is_space_statistics = (
                is_space_comparison or (not is_single_analysis and not is_group_analysis and SpaceStatisticsComposer.matches(context.query)))
            tool_name = (
                "space_comparison" if is_space_comparison else
                "picture_analysis" if is_single_analysis else
                "picture_group_analysis" if is_group_analysis else
                ("space_statistics" if is_space_statistics else "picture_keyword_search")
            )
            phase = tool_name
            self.java.append_event(
                signed.task_id, token, "tool_start",
                json.dumps({"tool": tool_name}, separators=(",", ":")),
            )
            if is_temporary_analysis:
                is_single_analysis = is_group_analysis = is_space_statistics = False
                result = ExecutionResult(f"本次输入为临时图片（{context.temporaryImage.width} × {context.temporaryImage.height}），不属于站内资产，没有永久图片 ID。", [], 0)
                tool_result = {"tool": "temporary_image_analysis"}
            elif context.allSpaces and is_space_statistics and not is_space_comparison:
                result = ExecutionResult("当前会话为全范围检索。空间统计请进入具体空间，或明确输入‘比较空间 ID1、ID2’；不会用公共图库统计冒充全范围统计。", [], 0)
                tool_result = {"tool": "scope_clarification"}
            elif is_space_comparison:
                summaries = self.java.get_space_comparison(signed.task_id, token)
                lines = ["已对明确指定且当前有权限的空间完成比较：", "",
                         "| 空间 ID | 图片数量 | 已用字节 |", "|---|---:|---:|"]
                for summary in summaries:
                    lines.append(f"| {summary.scope.spaceId} | {summary.usage.usedCount} | {summary.usage.usedSize} |")
                lines.extend(["", *[SpaceStatisticsComposer.compose(item) for item in summaries]])
                result = ExecutionResult("\n".join(lines), [], 0)
                tool_result = {"tool": tool_name, "spaces": [s.scope.spaceId for s in summaries]}
            elif is_single_analysis:
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
                    f"- 宽高比：{round(picture.width/picture.height,4) if picture.width and picture.height and picture.height>0 else '未知'}",
                    f"- 大小：{picture.size if picture.size is not None else '未知'} 字节",
                    f"- 标签：{picture.tags or '无'}",
                    f"- 上传人 ID：{picture.uploaderId or '未知'}；上传时间：{picture.createdAt or '未知'}",
                    f"- 空间：{picture.spaceId or '公共图库'}；主色：{picture.color or '未知'}",
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
            if not is_space_comparison and (is_single_analysis or is_group_analysis):
                result = ExecutionResult(
                    result.answer + "\n\n" + summarize_features(selected),
                    result.citations, result.candidate_count, result.intent_state)
            check_active()
            self.java.append_event(
                signed.task_id, token, "tool_result",
                json.dumps(tool_result, separators=(",", ":")),
            )
            for citation in result.citations:
                self.java.append_event(
                    signed.task_id, token, "citation",
                    json.dumps(citation, ensure_ascii=False, separators=(",", ":")),
                )
            publish(result.answer)
            if is_temporary_analysis:
                phase = "TEMPORARY_VISUAL_ANALYSIS"
                check_active()
                if self.vision and self.vision.enabled:
                    publish(result.answer + "\n\n视觉观察（不代表实验事实）：\n")
                    self.vision.analyze_stream(context.query, [context.temporaryImage],
                        lambda delta: publish(published_answer + delta), check_active)
                else:
                    publish(result.answer + "\n\n视觉模型未启用；未生成视觉结论。")
            if is_group_analysis:
                phase = "GROUP_SIMILARITY"
                result = self._add_group_similarity(
                    result, selected, context, signed, token, check_active)
                publish(result.answer)
            if not is_space_statistics and not is_temporary_analysis:
                phase = "VISUAL_ANALYSIS"
                result = self._add_visual_analysis(
                    result, context, signed, token, check_active, publish)
                publish(result.answer)
            check_active()
            publish_usage()
            self.java.update_state(signed.task_id, token, status="SUCCEEDED", stage="COMPLETED")
            outcome = "succeeded"
        except BudgetExceeded as error:
            outcome = "budget"
            if running:
                publish_usage()
                self._try_fail(signed.task_id, token, status="FAILED", stage="BUDGET_EXCEEDED",
                               error_code="BUDGET_EXCEEDED", error_message=failure_message("任务预算终止：" + str(error)))
        except TaskCancelled:
            outcome = "cancelled"
        except TaskDeadlineExceeded:
            outcome = "timeout"
            if running:
                publish_usage()
                self._try_fail(
                    signed.task_id, token, status="FAILED", stage="TIMEOUT",
                    error_code="TASK_TIMEOUT", error_message=failure_message("Agent 任务超过总执行时间限制"),
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
                publish_usage()
                self._try_fail(
                    signed.task_id,
                    token,
                    status="FAILED",
                    stage="INTERNAL_ERROR",
                    error_code="AGENT_INTERNAL_ERROR",
                    error_message=failure_message("Agent 执行失败，请稍后重试"),
                )
        finally:
            set_outcome(outcome)
            runtime_metrics.observe_task(outcome, time.monotonic() - started, empty_result)
            active_budget.reset(budget_token)
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
            if context.allSpaces:
                scope_key = ["public", *["space:" + value for value in context.allowedSpaceIds]]
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
        check_active: CheckActive, publish=None,
    ) -> ExecutionResult:
        if not self.vision or not self.vision.enabled or not result.citations:
            return result
        picture_ids = list(dict.fromkeys(
            item["pictureId"] for item in result.citations if item.get("pictureId")))[:20]
        if not picture_ids:
            return result
        if publish and isinstance(self.vision, VisionAnalyzer):
            return self._stream_visual_batches(result, context, signed, token, check_active, publish, picture_ids)
        batch_size = max(1, min(8, self.vision.max_pictures))
        observations = []
        successful_ids = []
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
                successful_ids.extend(item.pictureId for item in inputs)
                covered += len({item.pictureId for item in inputs})
                observations.append(f"批次 {offset // batch_size + 1}：\n" + analysis[:1200])
        self.java.append_event(
            signed.task_id, token, "tool_result",
            json.dumps({"tool": "vision_analysis", "count": covered,
                        "totalCount": len(picture_ids), "available": bool(observations)}))
        if not observations:
            return result
        reducer = getattr(self.vision, "summarize", None)
        summary = reducer(context.query, observations, successful_ids) if callable(reducer) else None
        check_active()
        if summary:
            observations.append("跨批汇总（基于各批摘要）：\n" + summary)
        return ExecutionResult(
            answer=(result.answer + f"\n\n视觉模型观察（覆盖 {covered}/{len(picture_ids)} 张，"
                    "不代表实验事实）：\n" + "\n\n".join(observations)),
            citations=result.citations,
            candidate_count=result.candidate_count,
            intent_state=result.intent_state,
        )

    def _stream_visual_batches(self, result, context, signed, token, check_active, publish, picture_ids):
        answer = result.answer + "\n\n视觉模型观察（不代表实验事实）：\n"
        publish(answer)
        observations, successful_ids = [], []
        def emit(delta):
            nonlocal answer
            answer += delta
            publish(answer)
        size = max(1, min(8, self.vision.max_pictures))
        for offset in range(0, len(picture_ids), size):
            check_active()
            batch = picture_ids[offset:offset+size]
            inputs = self.java.get_vision_inputs(signed.task_id, token, batch)
            if not inputs or any(p.pictureId not in batch for p in inputs):
                raise ValueError("visual batch unavailable")
            emit(f"\n批次 {offset//size+1}：\n")
            observation = self.vision.analyze_stream(context.query, inputs, emit, check_active)
            if observation:
                observations.append(observation)
                successful_ids.extend(p.pictureId for p in inputs)
        check_active()
        summary = self.vision.summarize(context.query, observations, successful_ids)
        check_active()
        if summary:
            emit("\n\n跨批汇总（基于各批摘要）：\n"+summary)
        emit(f"\n\n视觉分析覆盖 {len(set(successful_ids))}/{len(picture_ids)} 张。")
        return ExecutionResult(answer, result.citations, result.candidate_count, result.intent_state)

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
