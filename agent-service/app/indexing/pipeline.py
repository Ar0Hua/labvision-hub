from __future__ import annotations

import json
from urllib.parse import quote

import httpx
from pydantic import BaseModel, ConfigDict

from app.config import Settings
from app.indexing.features import PROMPT_VERSION, analyze_caption, download_image, extract_features
from app.security.worker_token import issue_worker_token


class IndexJob(BaseModel):
    model_config = ConfigDict(extra="forbid")

    jobId: str
    leaseToken: str
    pictureId: str
    operation: str
    scopeKey: str | None = None
    spaceId: str | None = None
    userId: str | None = None
    reviewStatus: int | None = None
    name: str | None = None
    introduction: str | None = None
    category: str | None = None
    tags: str | None = None
    picFormat: str | None = None
    picWidth: int | None = None
    picHeight: int | None = None
    picSize: int | None = None
    picColor: str | None = None
    createdAtEpoch: int | None = None
    sourceUpdatedAtEpoch: int | None = None
    temporaryUrl: str | None = None


class PictureIndexWorker:
    """Build explainable image features and two named Qdrant vectors."""

    def __init__(self, settings: Settings, java: httpx.Client | None = None,
                 dashscope: httpx.Client | None = None, qdrant: httpx.Client | None = None,
                 image: httpx.Client | None = None,
                 multimodal: httpx.Client | None = None) -> None:
        self._settings = settings
        self._java = java or httpx.Client(
            base_url=settings.java_base_url, timeout=settings.java_timeout_seconds)
        self._dashscope = dashscope or httpx.Client(
            base_url=settings.dashscope_base_url, timeout=settings.model_timeout_seconds)
        self._qdrant = qdrant or httpx.Client(
            base_url=settings.qdrant_url, timeout=settings.qdrant_timeout_seconds)
        self._image = image or httpx.Client(timeout=settings.model_timeout_seconds)
        self._multimodal = multimodal or httpx.Client(
            base_url=settings.image_embedding_base_url, timeout=settings.model_timeout_seconds)
        self._owned = (java is None, dashscope is None, qdrant is None,
                       image is None, multimodal is None)

    def process_once(self, limit: int = 10) -> int:
        jobs = self._claim(limit)
        for job in jobs:
            try:
                if job.operation == "DELETE":
                    self._delete(job)
                    self._ack(job, True, None, {"deleted": True})
                elif job.operation == "UPSERT":
                    feature = self._upsert(job)
                    self._ack(job, True, None, feature)
                else:
                    raise ValueError("unknown index operation")
            except Exception as error:
                self._ack(job, False, error.__class__.__name__, {})
        return len(jobs)

    def close(self) -> None:
        clients = (self._java, self._dashscope, self._qdrant, self._image, self._multimodal)
        for owned, client in zip(self._owned, clients):
            if owned:
                client.close()

    def _claim(self, limit: int) -> list[IndexJob]:
        data = self._java_call("POST", "/agent/internal/index/jobs/claim", json={"limit": limit})
        if not isinstance(data, list):
            raise RuntimeError("invalid index claim response")
        return [IndexJob.model_validate(item) for item in data]

    def _ack(self, job: IndexJob, success: bool, error: str | None, feature: dict) -> None:
        payload = {"leaseToken": job.leaseToken, "success": success, "errorMessage": error}
        payload.update(feature)
        self._java_call("POST", f"/agent/internal/index/jobs/{job.jobId}/ack", json=payload)

    def _java_call(self, method: str, path: str, **kwargs):
        token = issue_worker_token(self._settings.service_secret)
        response = self._java.request(
            method, path, headers={"Authorization": f"Bearer {token}"}, **kwargs)
        response.raise_for_status()
        body = response.json()
        if not isinstance(body, dict) or body.get("code") != 0:
            raise RuntimeError("Java index gateway rejected request")
        return body.get("data")

    def _upsert(self, job: IndexJob) -> dict:
        if not self._settings.dashscope_api_key or not job.scopeKey or not job.temporaryUrl:
            raise RuntimeError("image indexing is not configured")
        content = download_image(self._image, job.temporaryUrl)
        extracted = extract_features(content)
        caption, ocr = analyze_caption(
            self._dashscope, self._settings.dashscope_api_key,
            self._settings.caption_model, job.temporaryUrl)
        document = self._document(job, caption, ocr)
        text_vector = self._text_embedding(document)
        image_vector = self._image_embedding(job.temporaryUrl)
        payload = self._payload(job, extracted, caption, ocr)
        collection = quote(self._settings.qdrant_collection, safe="")
        response = self._qdrant.put(
            f"/collections/{collection}/points", params={"wait": "true"},
            headers=self._qdrant_headers(), json={"points": [{
                "id": int(job.pictureId),
                "vector": {"text_dense": text_vector, "image_dense": image_vector},
                "payload": payload,
            }]})
        response.raise_for_status()
        return {
            "caption": caption, "ocrText": ocr,
            "contentHash": extracted.content_hash,
            "phash": extracted.phash, "dhash": extracted.dhash,
            "blurScore": extracted.blur_score,
            "brightnessScore": extracted.brightness_score,
            "qualityFlags": json.dumps(extracted.quality_flags, ensure_ascii=False),
            "embeddingModel": (
                f"{self._settings.image_embedding_model}+{self._settings.embedding_model}"),
            "embeddingVersion": self._settings.feature_version,
            "captionModel": self._settings.caption_model,
            "promptVersion": PROMPT_VERSION,
            "sourceUpdatedAtEpoch": job.sourceUpdatedAtEpoch,
        }

    def _text_embedding(self, text: str) -> list[float]:
        response = self._dashscope.post(
            "/embeddings",
            headers={"Authorization": f"Bearer {self._settings.dashscope_api_key}"},
            json={"model": self._settings.embedding_model, "input": text,
                  "dimensions": self._settings.embedding_dimensions,
                  "encoding_format": "float"})
        response.raise_for_status()
        vector = response.json()["data"][0]["embedding"]
        return self._validate_vector(vector, self._settings.embedding_dimensions)

    def _image_embedding(self, image_url: str) -> list[float]:
        response = self._multimodal.post(
            "/services/embeddings/multimodal-embedding/multimodal-embedding",
            headers={"Authorization": f"Bearer {self._settings.dashscope_api_key}"},
            json={"model": self._settings.image_embedding_model,
                  "input": {"contents": [{"image": image_url}]},
                  "parameters": {"dimension": self._settings.image_embedding_dimensions}})
        response.raise_for_status()
        vector = response.json()["output"]["embeddings"][0]["embedding"]
        return self._validate_vector(vector, self._settings.image_embedding_dimensions)

    @staticmethod
    def _validate_vector(vector, expected: int) -> list[float]:
        if not isinstance(vector, list) or len(vector) != expected:
            raise ValueError("embedding dimension mismatch")
        return [float(value) for value in vector]

    def _delete(self, job: IndexJob) -> None:
        collection = quote(self._settings.qdrant_collection, safe="")
        response = self._qdrant.post(
            f"/collections/{collection}/points/delete", params={"wait": "true"},
            headers=self._qdrant_headers(), json={"points": [int(job.pictureId)]})
        response.raise_for_status()

    def _qdrant_headers(self) -> dict[str, str]:
        return ({"api-key": self._settings.qdrant_api_key}
                if self._settings.qdrant_api_key else {})

    def _payload(self, job: IndexJob, extracted, caption: str, ocr: str) -> dict:
        from app.retrieval.visual_filters import rgb
        channels = rgb(job.picColor)
        return {
            "colorR": channels[0] if channels else None,
            "colorG": channels[1] if channels else None,
            "colorB": channels[2] if channels else None,
            "pictureId": job.pictureId, "scopeKey": job.scopeKey,
            "spaceId": job.spaceId, "userId": job.userId,
            "reviewStatus": job.reviewStatus, "isDelete": 0,
            "category": job.category, "tags": self._tags(job.tags),
            "picFormat": job.picFormat, "picWidth": job.picWidth,
            "picHeight": job.picHeight, "picSize": job.picSize,
            "aspectRatio": (job.picWidth / job.picHeight
                            if job.picWidth and job.picHeight and job.picWidth > 0 and job.picHeight > 0 else None),
            "picColor": job.picColor, "createdAtEpoch": job.createdAtEpoch,
            "sourceUpdatedAtEpoch": job.sourceUpdatedAtEpoch,
            "featureVersion": self._settings.feature_version,
            "contentHash": extracted.content_hash, "phash": extracted.phash,
            "dhash": extracted.dhash, "blurScore": extracted.blur_score,
            "brightnessScore": extracted.brightness_score,
            "qualityFlags": extracted.quality_flags,
            "caption": caption, "ocrText": ocr,
        }

    @classmethod
    def _document(cls, job: IndexJob, caption: str, ocr: str) -> str:
        values = [job.name, job.introduction, job.category, caption, ocr, *cls._tags(job.tags)]
        return "\n".join(" ".join(value.split()) for value in values
                         if value and value.strip())[:8000]

    @staticmethod
    def _tags(value: str | None) -> list[str]:
        if not value:
            return []
        try:
            parsed = json.loads(value)
        except ValueError:
            return []
        return [item for item in parsed if isinstance(item, str)] if isinstance(parsed, list) else []
