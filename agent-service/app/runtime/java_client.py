from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field, field_validator
from urllib.parse import urlsplit

from app.analysis.space_statistics import SpaceStatistics
from app.config import Settings
from app.runtime.budget import reserve


class TemporaryInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    temporaryId: str = Field(pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
    width: int = Field(ge=1, le=1024)
    height: int = Field(ge=1, le=1024)
    dataUrl: str = Field(pattern=r"^data:image/jpeg;base64,[A-Za-z0-9+/]+={0,2}$", max_length=1398130, repr=False, exclude=True)


class TaskContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    taskId: str
    conversationId: str
    userId: str
    spaceId: str | None
    allSpaces: bool = False
    allowedSpaceIds: list[str] = Field(default_factory=list, max_length=50)
    userRole: str | None = None
    query: str
    examplePictureIds: list[str] = Field(default_factory=list, max_length=20)
    status: str
    temporaryImageId: str | None = None
    temporaryImage: TemporaryInput | None = Field(default=None, exclude=True, repr=False)


class PictureFeatures(BaseModel):
    model_config = ConfigDict(extra="forbid")
    contentHash: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    phash: str | None = Field(default=None, pattern=r"^[0-9a-f]{16}$")
    dhash: str | None = Field(default=None, pattern=r"^[0-9a-f]{16}$")
    blurScore: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    brightnessScore: float | None = Field(default=None, ge=0, le=255, allow_inf_nan=False)
    qualityFlags: str | None = None
    caption: str | None = None
    ocrText: str | None = None
    indexedAt: str | None = None


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
    uploaderId: str | None = None
    color: str | None = None
    createdAt: str | int | None = None
    features: PictureFeatures | None = None


class VisionInput(PictureCandidate):
    temporaryUrl: str
    expiresInSeconds: int = Field(ge=30, le=300)

    @field_validator("temporaryUrl")
    @classmethod
    def secure_url(cls, value: str) -> str:
        parsed = urlsplit(value)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("vision input must be an HTTPS URL without embedded credentials")
        return value


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

    def get_temporary_image(self, task_id: str, token: str) -> TemporaryInput:
        return TemporaryInput.model_validate(self._request(
            "GET", f"/agent/internal/tasks/{task_id}/temporary-image", token))

    def get_space_comparison(self, task_id: str, token: str) -> list[SpaceStatistics]:
        data = self._request("GET", f"/agent/internal/tasks/{task_id}/spaces/compare", token)
        if not isinstance(data, list) or not 2 <= len(data) <= 5:
            raise JavaGatewayError("invalid space comparison")
        return [SpaceStatistics.model_validate(item) for item in data]

    def get_space_statistics(self, task_id: str, token: str) -> SpaceStatistics:
        data = self._request(
            "GET", f"/agent/internal/tasks/{task_id}/spaces/summary", token)
        return SpaceStatistics.model_validate(data)

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
        tags: list[str] | None = None, limit: int = 10, filters: dict[str, Any] | None = None,
    ) -> list[PictureCandidate]:
        body = {"searchText": search_text, "category": category, "tags": tags or [], "limit": limit}
        allowed = ("formats", "createdAfter", "createdBefore", "minWidth", "minHeight",
                   "maxSizeBytes", "sort", "uploaderId", "minAspectRatio", "maxAspectRatio",
                   "targetColor", "colorTolerance", "brightness")
        for key in allowed:
            if filters and key in filters:
                body[key] = filters[key]
        data = self._request(
            "POST",
            f"/agent/internal/tasks/{task_id}/pictures/search",
            token,
            json=body,
        )
        if not isinstance(data, list):
            raise JavaGatewayError("Java picture search returned invalid data")
        return [PictureCandidate.model_validate(item) for item in data]

    def authorize_pictures(
        self, task_id: str, token: str, picture_ids: list[str]
    ) -> list[PictureCandidate]:
        integer_ids = []
        for picture_id in picture_ids[:20]:
            if not picture_id.isdigit() or int(picture_id) < 1 or int(picture_id) > 9_223_372_036_854_775_807:
                raise JavaGatewayError("external index returned invalid picture ID")
            integer_ids.append(int(picture_id))
        if not integer_ids:
            return []
        data = self._request(
            "POST",
            f"/agent/internal/tasks/{task_id}/pictures/details",
            token,
            json={"pictureIds": integer_ids},
        )
        if not isinstance(data, list):
            raise JavaGatewayError("Java picture authorization returned invalid data")
        return [PictureCandidate.model_validate(item) for item in data]

    def get_vision_inputs(
        self, task_id: str, token: str, picture_ids: list[str]
    ) -> list[VisionInput]:
        integer_ids = [int(value) for value in picture_ids[:8] if value.isdigit() and int(value) > 0]
        if len(integer_ids) != min(len(picture_ids), 8) or not integer_ids:
            raise JavaGatewayError("vision analysis received invalid picture IDs")
        data = self._request(
            "POST",
            f"/agent/internal/tasks/{task_id}/pictures/vision-inputs",
            token,
            json={"pictureIds": integer_ids},
        )
        if not isinstance(data, list):
            raise JavaGatewayError("Java vision input endpoint returned invalid data")
        return [VisionInput.model_validate(item) for item in data]

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def _request(self, method: str, path: str, token: str, **kwargs: Any) -> Any:
        if not path.endswith(("/events", "/state")):
            reserve()
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
