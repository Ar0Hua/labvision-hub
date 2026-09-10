from collections.abc import Callable
import re

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse

from app.config import Settings
from app.runtime.registry import TaskRegistry
from app.runtime.runner import TaskRunner
from app.security.service_token import InvalidServiceToken, verify_service_token
from app.observability.metrics import runtime_metrics
from app.observability.tracing import run_traced, configure_logging

TASK_ID = re.compile(r"^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$")


def create_app(
    settings_provider: Callable[[], Settings] = Settings.from_env,
    runner_factory: Callable[[Settings], TaskRunner] = TaskRunner.from_settings,
    registry: TaskRegistry | None = None,
) -> FastAPI:
    service = FastAPI(title="LabVision Search & Insight Agent", version="0.1.0")
    configure_logging()
    replay_guard = registry or TaskRegistry()

    @service.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @service.get("/metrics", response_class=PlainTextResponse)
    def metrics() -> str:
        return runtime_metrics.render()

    @service.post("/internal/tasks/{task_id}/run", status_code=202)
    def run_task(
        task_id: str,
        background_tasks: BackgroundTasks,
        authorization: str = Header(...),
        traceparent: str | None = Header(default=None),
    ) -> JSONResponse:
        if not TASK_ID.fullmatch(task_id) or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="invalid service token")
        token = authorization[7:]
        try:
            settings = settings_provider()
            context = verify_service_token(token, task_id, settings.service_secret)
        except (InvalidServiceToken, RuntimeError):
            raise HTTPException(status_code=401, detail="invalid service token") from None
        accepted = replay_guard.accept(token, context.expires_at)
        if accepted:
            background_tasks.add_task(run_traced, runner_factory(settings), context, token, traceparent)
        return JSONResponse(status_code=202, content={"accepted": accepted, "taskId": task_id})

    return service


app = create_app()
