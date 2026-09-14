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
    search_scope: str | None
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
        if resume:
            from app.runtime.scope import validate_scope, matches_scope
            validate_scope(context, saved.values.get('search_scope'))
        if resume and 'retrieve' not in saved.next:
            ids = list(dict.fromkeys(item['pictureId'] for item in saved.values.get('citations',[]) if item.get('pictureId')))
            current = []
            for offset in range(0,len(ids),20):
                check_active()
                current.extend(p.pictureId for p in authorize(ids[offset:offset+20])
                               if matches_scope(p, saved.values.get('search_scope')))
            if set(current) != set(ids):
                raise ValueError('checkpoint citations are no longer authorized')
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
            from app.runtime.scope import validate_scope
            selected_scope = context.searchScope if context.searchScope is not None else state.get('search_scope')
            validate_scope(context, selected_scope)
            effective = context.model_copy(update={'searchScope': selected_scope})
            scope_changed = selected_scope != state.get('search_scope')
            previous_intent = state.get('intent_state')
            if scope_changed and previous_intent:
                previous_intent = {k:v for k,v in previous_intent.items()
                                   if k not in ('examplePictureIds', 'excludePictureIds')}
            stateful = getattr(self._executor, "execute_with_state", None)
            if callable(stateful):
                previous_result_ids = [
                    item["pictureId"] for item in state.get("citations", [])
                    if item.get("pictureId")
                ][:20]
                result = stateful(
                    effective, search, authorize, check_active,
                    previous_intent, [] if scope_changed else previous_result_ids,
                )
            else:
                result = self._executor.execute(effective, search, authorize, check_active)
            return {
                "stage": "RETRIEVED",
                "search_scope": selected_scope,
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
