from urllib.parse import quote

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

    def search(self, text: str, scope_key: str, limit: int = 20) -> list[str]:
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
                    "filter": {"must": [{"key": "scopeKey", "match": {"value": scope_key}}]},
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
