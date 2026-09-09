from urllib.parse import quote
from datetime import date, datetime, time, timedelta, timezone

import httpx

from app.config import Settings


class SemanticRetriever:
    """DashScope text embedding + Qdrant candidate IDs. Never an authorization source."""

    def __init__(
        self,
        settings: Settings,
        embedding_client: httpx.Client | None = None,
        qdrant_client: httpx.Client | None = None,
    ) -> None:
        self._settings = settings
        self._embedding_client = embedding_client
        self._qdrant_client = qdrant_client

    @property
    def enabled(self) -> bool:
        return bool(self._settings.dashscope_api_key and self._settings.embedding_model)

    def search(self, text: str, scope_key: str, limit: int = 20,
               filters: dict | None = None) -> list[str]:
        if not self.enabled:
            return []
        embedding_client = self._embedding_client or httpx.Client(
            base_url=self._settings.dashscope_base_url,
            timeout=self._settings.model_timeout_seconds,
        )
        qdrant_client = self._qdrant_client or httpx.Client(
            base_url=self._settings.qdrant_url,
            timeout=self._settings.qdrant_timeout_seconds,
        )
        try:
            embedding_response = embedding_client.post(
                "/embeddings",
                headers={"Authorization": f"Bearer {self._settings.dashscope_api_key}"},
                json={
                    "model": self._settings.embedding_model,
                    "input": text,
                    "dimensions": self._settings.embedding_dimensions,
                    "encoding_format": "float",
                },
            )
            embedding_response.raise_for_status()
            vector = embedding_response.json()["data"][0]["embedding"]
            if not isinstance(vector, list) or not vector:
                raise ValueError("invalid embedding")
            headers = {}
            if self._settings.qdrant_api_key:
                headers["api-key"] = self._settings.qdrant_api_key
            collection = quote(self._settings.qdrant_collection, safe="")
            response = qdrant_client.post(
                f"/collections/{collection}/points/query",
                headers=headers,
                json={
                    "query": vector,
                    "using": "text_dense",
                    "filter": self._filter(scope_key, filters),
                    "limit": min(max(limit, 1), 20),
                    "with_payload": ["pictureId"],
                    "with_vector": False,
                },
            )
            response.raise_for_status()
            result = response.json().get("result", {})
            points = result.get("points", []) if isinstance(result, dict) else []
            ids = []
            for point in points:
                picture_id = point.get("payload", {}).get("pictureId")
                if isinstance(picture_id, str) and picture_id.isdigit() and picture_id not in ids:
                    ids.append(picture_id)
            return ids[:limit]
        finally:
            if self._embedding_client is None:
                embedding_client.close()
            if self._qdrant_client is None:
                qdrant_client.close()

    def search_by_pictures(
        self, picture_ids: list[str], scope_key: str, limit: int = 20, filters: dict | None = None,
    ) -> list[str]:
        """Query Qdrant by already indexed image vectors; Java reauthorizes every result."""
        examples = []
        for picture_id in picture_ids[:5]:
            if not picture_id.isdigit() or int(picture_id) < 1:
                raise ValueError("invalid example picture ID")
            if picture_id not in examples:
                examples.append(picture_id)
        if not examples:
            return []
        qdrant_client = self._qdrant_client or httpx.Client(
            base_url=self._settings.qdrant_url,
            timeout=self._settings.qdrant_timeout_seconds,
        )
        try:
            headers = ({"api-key": self._settings.qdrant_api_key}
                       if self._settings.qdrant_api_key else {})
            collection = quote(self._settings.qdrant_collection, safe="")
            ranked: list[str] = []
            query_filter = self._filter(scope_key, filters)
            query_filter.setdefault("must_not", []).append(
                {"key": "pictureId", "match": {"any": examples}}
            )
            for picture_id in examples:
                response = qdrant_client.post(
                    f"/collections/{collection}/points/query",
                    headers=headers,
                    json={
                        "query": int(picture_id),
                        "using": "image_dense",
                        "filter": query_filter,
                        "limit": min(max(limit, 1), 20),
                        "with_payload": ["pictureId"],
                        "with_vector": False,
                    },
                )
                response.raise_for_status()
                result = response.json().get("result", {})
                points = result.get("points", []) if isinstance(result, dict) else []
                for point in points:
                    candidate = point.get("payload", {}).get("pictureId")
                    if (isinstance(candidate, str) and candidate.isdigit()
                            and candidate not in examples and candidate not in ranked):
                        ranked.append(candidate)
            return ranked[:limit]
        finally:
            if self._qdrant_client is None:
                qdrant_client.close()

    @staticmethod
    def _filter(scope_key: str, filters: dict | None = None) -> dict:
        values = filters or {}
        must = [
            {"key": "scopeKey", "match": {"value": scope_key}},
            {"key": "isDelete", "match": {"value": 0}},
        ]
        if scope_key == "public":
            must.append({"key": "reviewStatus", "match": {"value": 1}})
        if values.get("category"):
            must.append({"key": "category", "match": {"value": values["category"]}})
        for tag in values.get("tags") or []:
            must.append({"key": "tags", "match": {"value": tag}})
        if values.get("formats"):
            must.append({"key": "picFormat", "match": {"any": values["formats"]}})
        zone = timezone(timedelta(hours=8))
        if values.get("createdAfter"):
            after = datetime.combine(date.fromisoformat(values["createdAfter"]), time.min, zone)
            must.append({"key": "createdAtEpoch", "range": {"gte": int(after.timestamp())}})
        if values.get("createdBefore"):
            next_day = date.fromisoformat(values["createdBefore"]) + timedelta(days=1)
            before = datetime.combine(next_day, time.min, zone)
            must.append({"key": "createdAtEpoch", "range": {"lt": int(before.timestamp())}})
        if values.get("minWidth") is not None:
            must.append({"key": "picWidth", "range": {"gte": values["minWidth"]}})
        if values.get("minHeight") is not None:
            must.append({"key": "picHeight", "range": {"gte": values["minHeight"]}})
        if values.get("maxSizeBytes") is not None:
            must.append({"key": "picSize", "range": {"lte": values["maxSizeBytes"]}})
        result = {"must": must}
        if values.get("excludePictureIds"):
            result["must_not"] = [{
                "key": "pictureId", "match": {"any": values["excludePictureIds"]},
            }]
        return result
