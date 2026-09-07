from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict

from app.config import Settings


class TaskContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    taskId: str
    conversationId: str
    userId: str
    spaceId: str | None
    query: str


class PictureCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pictureId: str
    spaceId: str | None
    name: str | None = None
    introduction: str | None = None
    category: str | None = None
    tags: str | None = None
    width: int | None = None
    height: int | None = None
    size: int | None = None
    format: str | None = None


class JavaGatewayError(RuntimeError):
    pass


class JavaTaskClient:
    def __init__(self, settings: Settings, client: httpx.Client | None = None) -> None:
        self._client = client or httpx.Client(
            base_url=settings.java_base_url,
            timeout=settings.java_timeout_seconds,
        )
        self._owns_client = client is None

    def get_context(self, task_id: str, token: str) -> TaskContext:
        data = self._request("GET", f"/agent/internal/tasks/{task_id}/context", token)
        return TaskContext.model_validate(data)

    def update_state(
        self,
        task_id: str,
        token: str,
        *,
        status: str,
        stage: str,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> None:
        self._request(
            "POST",
            f"/agent/internal/tasks/{task_id}/state",
            token,
            json={
                "status": status,
                "stage": stage,
                "errorCode": error_code,
                "errorMessage": error_message,
            },
        )

    def append_event(self, task_id: str, token: str, event_type: str, payload_json: str) -> None:
        self._request(
            "POST",
            f"/agent/internal/tasks/{task_id}/events",
            token,
            json={"eventType": event_type, "payloadJson": payload_json},
        )

    def search_pictures(
        self, task_id: str, token: str, *, search_text: str, category: str | None = None,
        tags: list[str] | None = None, limit: int = 10
    ) -> list[PictureCandidate]:
        data = self._request(
            "POST",
            f"/agent/internal/tasks/{task_id}/pictures/search",
            token,
            json={"searchText": search_text, "category": category, "tags": tags or [], "limit": limit},
        )
        if not isinstance(data, list):
            raise JavaGatewayError("Java picture search returned invalid data")
        return [PictureCandidate.model_validate(item) for item in data]

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def _request(self, method: str, path: str, token: str, **kwargs: Any) -> Any:
        response = self._client.request(
            method, path, headers={"Authorization": f"Bearer {token}"}, **kwargs
        )
        response.raise_for_status()
        try:
            body = response.json()
        except ValueError as error:
            raise JavaGatewayError("Java gateway returned invalid JSON") from error
        if not isinstance(body, dict) or body.get("code") != 0:
            raise JavaGatewayError("Java gateway rejected the task callback")
        return body.get("data")
