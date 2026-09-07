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

    def __init__(self, executor: BaseExecutor, checkpointer: object) -> None:
        self._executor = executor
        self._checkpointer = checkpointer

    def execute(
        self,
        context: TaskContext,
        search: SearchPictures,
        authorize: AuthorizePictures,
        check_active: CheckActive,
    ) -> ExecutionResult:
        graph = self._compile(context, search, authorize, check_active)
        output = graph.invoke(
            {"task_id": context.taskId, "query": context.query},
            self._config(context),
        )
        return ExecutionResult(
            answer=output["answer"],
            citations=output.get("citations", []),
            candidate_count=output.get("candidate_count", 0),
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

        def retrieve(_: WorkflowState) -> WorkflowState:
            check_active()
            result = self._executor.execute(context, search, authorize, check_active)
            return {
                "stage": "RETRIEVED",
                "answer": result.answer,
                "citations": result.citations,
                "candidate_count": result.candidate_count,
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

    @staticmethod
    def _config(context: TaskContext) -> dict:
        return {
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
            return LangGraphWorkflow(self._executor, checkpointer).execute(
                context, search, authorize, check_active
            )
