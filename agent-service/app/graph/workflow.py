from typing import Annotated, TypedDict

from app.config import Settings
from app.retrieval.keyword_executor import (
    AuthorizePictures,
    CheckActive,
    ExecutionResult,
    SearchPictures,
)
from app.runtime.java_client import TaskContext


class TurnSummary(TypedDict):
    query: str
    pictureIds: list[str]


def _recent_turns(left: list[TurnSummary], right: list[TurnSummary]) -> list[TurnSummary]:
    """Keep bounded structured memory instead of an unlimited transcript."""
    return (left + right)[-8:]


class WorkflowState(TypedDict, total=False):
    task_id: str
    query: str
    stage: str
    answer: str
    citations: list[dict[str, str | None]]
    candidate_count: int
    recent_turns: Annotated[list[TurnSummary], _recent_turns]
    intent_state: dict


class BaseExecutor:
    def execute(
        self,
        context: TaskContext,
        search: SearchPictures,
        authorize: AuthorizePictures,
        check_active: CheckActive,
    ) -> ExecutionResult:
        raise NotImplementedError


class LangGraphWorkflow:
    """Three-stage retrieval graph with per-user, per-conversation checkpoints."""

    def __init__(self, executor: BaseExecutor, checkpointer: object, max_steps: int = 6) -> None:
        self._executor = executor
        self._checkpointer = checkpointer
        self._max_steps = max_steps

    def execute(
        self,
        context: TaskContext,
        search: SearchPictures,
        authorize: AuthorizePictures,
        check_active: CheckActive,
    ) -> ExecutionResult:
        graph = self._compile(context, search, authorize, check_active)
        config = self._config(context)
        saved = graph.get_state(config)
        resume = bool(saved.next and saved.values.get("task_id") == context.taskId)
        output = graph.invoke(
            None if resume else {"task_id": context.taskId, "query": context.query}, config,
        )
        return ExecutionResult(
            answer=output["answer"],
            citations=output.get("citations", []),
            candidate_count=output.get("candidate_count", 0),
            intent_state=output.get("intent_state"),
        )

    def state(self, context: TaskContext) -> WorkflowState:
        graph = self._compile(context, lambda *_: [], lambda _: [], lambda: None)
        return graph.get_state(self._config(context)).values

    def _compile(
        self,
        context: TaskContext,
        search: SearchPictures,
        authorize: AuthorizePictures,
        check_active: CheckActive,
    ):
        try:
            from langgraph.graph import END, START, StateGraph
        except ImportError as error:
            raise RuntimeError("LangGraph dependency is not installed") from error

        def prepare(_: WorkflowState) -> WorkflowState:
            check_active()
            return {"stage": "PLANNING"}

        def retrieve(state: WorkflowState) -> WorkflowState:
            check_active()
            stateful = getattr(self._executor, "execute_with_state", None)
            if callable(stateful):
                previous_result_ids = [
                    item["pictureId"] for item in state.get("citations", [])
                    if item.get("pictureId")
                ][:20]
                result = stateful(
                    context, search, authorize, check_active,
                    state.get("intent_state"), previous_result_ids,
                )
            else:
                result = self._executor.execute(context, search, authorize, check_active)
            return {
                "stage": "RETRIEVED",
                "answer": result.answer,
                "citations": result.citations,
                "candidate_count": result.candidate_count,
                "intent_state": result.intent_state or state.get("intent_state"),
            }

        def complete(state: WorkflowState) -> WorkflowState:
            check_active()
            return {
                "stage": "COMPLETED",
                "recent_turns": [{
                    "query": context.query,
                    "pictureIds": [
                        item["pictureId"] for item in state.get("citations", [])
                        if item.get("pictureId")
                    ][:20],
                }],
            }

        builder = StateGraph(WorkflowState)
        builder.add_node("prepare", prepare)
        builder.add_node("retrieve", retrieve)
        builder.add_node("complete", complete)
        builder.add_edge(START, "prepare")
        builder.add_edge("prepare", "retrieve")
        builder.add_edge("retrieve", "complete")
        builder.add_edge("complete", END)
        return builder.compile(checkpointer=self._checkpointer)

    def _config(self, context: TaskContext) -> dict:
        return {
            "recursion_limit": self._max_steps,
            "configurable": {
                "thread_id": f"{context.userId}:{context.conversationId}",
            }
        }


class RedisCheckpointWorkflow:
    """Open a Redis saver for each run so lifecycle follows the background task."""

    def __init__(self, executor: BaseExecutor, settings: Settings) -> None:
        self._executor = executor
        self._url = settings.checkpoint_redis_url
        self._ttl = settings.checkpoint_ttl_minutes
        self._max_steps = settings.max_graph_steps

    def execute(
        self,
        context: TaskContext,
        search: SearchPictures,
        authorize: AuthorizePictures,
        check_active: CheckActive,
    ) -> ExecutionResult:
        try:
            from langgraph.checkpoint.redis import RedisSaver
        except ImportError as error:
            raise RuntimeError("Redis checkpoint dependency is not installed") from error
        if self._ttl < 1:
            raise ValueError("checkpoint TTL must be positive")
        with RedisSaver.from_conn_string(
            self._url,
            ttl={"default_ttl": self._ttl, "refresh_on_read": True},
        ) as checkpointer:
            checkpointer.setup()
            return LangGraphWorkflow(self._executor, checkpointer, self._max_steps).execute(
                context, search, authorize, check_active
            )
