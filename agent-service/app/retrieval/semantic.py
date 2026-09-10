from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
import math
from urllib.parse import quote

import httpx
from app.runtime.http_client import client as managed_client

from app.config import Settings
from app.runtime.budget import reserve, reserve_model, record_usage
from app.observability.tracing import traced


@dataclass(frozen=True)
class PictureSimilarityMatrix:
    picture_ids: list[str]
    scores: list[list[float | None]]


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

    @traced("retrieval.text_dense")
    def search(self, text: str, scope_key: str, limit: int = 20,
               filters: dict | None = None) -> list[str]:
        if not self.enabled:
            return []
        embedding_client = self._embedding_client or managed_client(
            base_url=self._settings.dashscope_base_url,
            timeout=self._settings.model_timeout_seconds,
        )
        qdrant_client = self._qdrant_client or managed_client(
            base_url=self._settings.qdrant_url,
            timeout=self._settings.qdrant_timeout_seconds,
        )
        try:
            reserve_model(self._settings.embedding_model, text)
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
            record_usage(self._settings.embedding_model, embedding_response.json())
            vector = embedding_response.json()["data"][0]["embedding"]
            if not isinstance(vector, list) or not vector:
                raise ValueError("invalid embedding")
            headers = {}
            if self._settings.qdrant_api_key:
                headers["api-key"] = self._settings.qdrant_api_key
            collection = quote(self._settings.qdrant_collection, safe="")
            reserve()
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

    @traced("retrieval.image_example")
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
        qdrant_client = self._qdrant_client or managed_client(
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
                reserve()
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

    def search_by_image_data(self, data_url: str, scope_key, limit: int = 20,
                             filters: dict | None = None) -> list[str]:
        """Ephemeral image embedding; never upsert the input into the asset index."""
        return self._search_multimodal({"image":data_url}, scope_key, limit, filters)

    def search_visual_text(self, text: str, scope_key, limit: int = 20,
                           filters: dict | None = None) -> list[str]:
        """Use the same multimodal model as indexed pictures, not the metadata embedding."""
        return self._search_multimodal({"text":text[:500]}, scope_key, limit, filters)

    @traced("retrieval.multimodal")
    def _search_multimodal(self, content: dict, scope_key, limit, filters):
        query_filter = self._filter(scope_key, filters)
        embedding = self._embedding_client or managed_client(
            base_url=self._settings.image_embedding_base_url,
            timeout=self._settings.model_timeout_seconds)
        qdrant = self._qdrant_client or managed_client(
            base_url=self._settings.qdrant_url, timeout=self._settings.qdrant_timeout_seconds)
        try:
            reserve_model(self._settings.image_embedding_model, content.get("text", "temporary image"),
                          pictures=1 if "image" in content else 0)
            response = embedding.post("/services/embeddings/multimodal-embedding/multimodal-embedding",
                headers={"Authorization": f"Bearer {self._settings.dashscope_api_key}"},
                json={"model": self._settings.image_embedding_model,
                      "input": {"contents": [content]},
                      "parameters": {"dimension": self._settings.image_embedding_dimensions}})
            response.raise_for_status()
            body = response.json()
            record_usage(self._settings.image_embedding_model, body)
            vector = body["output"]["embeddings"][0]["embedding"]
            if (not isinstance(vector, list) or len(vector) != self._settings.image_embedding_dimensions
                    or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in vector)):
                raise ValueError("invalid temporary image embedding")
            reserve()
            response = qdrant.post(f"/collections/{quote(self._settings.qdrant_collection, safe='')}/points/query",
                headers={"api-key": self._settings.qdrant_api_key} if self._settings.qdrant_api_key else {},
                json={"query": vector, "using": "image_dense", "filter": query_filter,
                      "limit": min(max(limit, 1), 20), "with_payload": ["pictureId"], "with_vector": False})
            response.raise_for_status()
            ids = [p.get("payload", {}).get("pictureId") for p in response.json()["result"]["points"]]
            return list(dict.fromkeys(v for v in ids if isinstance(v, str) and v.isdigit()))[:20]
        finally:
            if self._embedding_client is None:
                embedding.close()
            if self._qdrant_client is None:
                qdrant.close()

    @traced("retrieval.image_matrix")
    def picture_similarity_matrix(
        self, picture_ids: list[str], scope_key: str,
    ) -> PictureSimilarityMatrix:
        """Read pairwise cosine similarities for an already-authorized picture group."""
        self._validate_similarity_request(picture_ids, scope_key)
        selected = list(picture_ids)
        selected_set = set(selected)
        pair_scores: dict[tuple[str, str], list[float]] = {}
        qdrant_client = self._qdrant_client or managed_client(
            base_url=self._settings.qdrant_url,
            timeout=self._settings.qdrant_timeout_seconds,
        )
        try:
            headers = ({"api-key": self._settings.qdrant_api_key}
                       if self._settings.qdrant_api_key else {})
            collection = quote(self._settings.qdrant_collection, safe="")
            for picture_id in selected:
                query_filter = self._filter(scope_key)
                query_filter.setdefault("must", []).append(
                    {"key": "pictureId", "match": {"any": selected}}
                )
                query_filter["must_not"] = [
                    {"key": "pictureId", "match": {"value": picture_id}}
                ]
                reserve()
                response = qdrant_client.post(
                    f"/collections/{collection}/points/query",
                    headers=headers,
                    json={
                        "query": int(picture_id),
                        "using": "image_dense",
                        "filter": query_filter,
                        "limit": len(selected) - 1,
                        "with_payload": ["pictureId"],
                        "with_vector": False,
                    },
                )
                response.raise_for_status()
                result = response.json().get("result", {})
                points = result.get("points", []) if isinstance(result, dict) else []
                for point in points:
                    candidate = point.get("payload", {}).get("pictureId")
                    if (not isinstance(candidate, str) or candidate not in selected_set
                            or candidate == picture_id):
                        continue
                    score = point.get("score")
                    if (isinstance(score, bool) or not isinstance(score, (int, float))
                            or not math.isfinite(score) or score < -1 or score > 1):
                        raise ValueError("invalid Qdrant image similarity score")
                    pair = tuple(sorted((picture_id, candidate), key=int))
                    pair_scores.setdefault(pair, []).append(float(score))
            scores: list[list[float | None]] = []
            for left in selected:
                row: list[float | None] = []
                for right in selected:
                    if left == right:
                        row.append(1.0)
                        continue
                    values = pair_scores.get(tuple(sorted((left, right), key=int)))
                    row.append(sum(values) / len(values) if values else None)
                scores.append(row)
            return PictureSimilarityMatrix(selected, scores)
        finally:
            if self._qdrant_client is None:
                qdrant_client.close()

    @staticmethod
    def _validate_similarity_request(picture_ids: list[str], scope_key: str) -> None:
        if isinstance(scope_key, list):
            SemanticRetriever._filter(scope_key)
            for key in scope_key:
                SemanticRetriever._validate_similarity_request(picture_ids, key)
            return
        if not 2 <= len(picture_ids) <= 20 or len(set(picture_ids)) != len(picture_ids):
            raise ValueError("picture similarity requires 2 to 20 unique picture IDs")
        if any(not value.isdigit() or not 1 <= int(value) <= 9223372036854775807
               for value in picture_ids):
            raise ValueError("invalid picture ID")
        if scope_key != "public":
            if (not scope_key.startswith("space:") or not scope_key[6:].isdigit()
                    or int(scope_key[6:]) < 1):
                raise ValueError("invalid scope key")

    @staticmethod
    def _filter(scope_key: str, filters: dict | None = None) -> dict:
        values = filters or {}
        if isinstance(scope_key,list):
            if not scope_key or len(scope_key)>51 or len(set(scope_key))!=len(scope_key):
                raise ValueError("invalid authorized scope list")
            for key in scope_key:
                if key!="public" and (not key.startswith("space:") or not key[6:].isdigit() or int(key[6:])<1):
                    raise ValueError("invalid scope key")
            return {"should":[SemanticRetriever._filter(key,values) for key in scope_key]}
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
        if values.get("uploaderId"):
            must.append({"key": "userId", "match": {"value": values["uploaderId"]}})
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
        ratio_range = {}
        if values.get("minAspectRatio") is not None:
            ratio_range["gte"] = values["minAspectRatio"]
        if values.get("maxAspectRatio") is not None:
            ratio_range["lte"] = values["maxAspectRatio"]
        if ratio_range:
            must.append({"key": "aspectRatio", "range": ratio_range})
        from app.retrieval.visual_filters import vector_conditions
        must.extend(vector_conditions(values))
        result = {"must": must}
        if values.get("excludePictureIds"):
            result["must_not"] = [{
                "key": "pictureId", "match": {"any": values["excludePictureIds"]},
            }]
        return result
