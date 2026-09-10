import argparse
import json
import time
from urllib.parse import quote

import httpx
from app.runtime.http_client import client as managed_client
from app.indexing.pipeline import PictureIndexWorker
from pydantic import BaseModel, ConfigDict

from app.config import Settings
from app.security.worker_token import issue_worker_token


class IndexJob(BaseModel):
    model_config = ConfigDict(extra="forbid")

    jobId: str
    leaseToken: str
    pictureId: str
    operation: str
    scopeKey: str | None = None
    name: str | None = None
    introduction: str | None = None
    category: str | None = None
    tags: str | None = None


class LegacyPictureIndexWorker:
    def __init__(
        self,
        settings: Settings,
        java: httpx.Client | None = None,
        dashscope: httpx.Client | None = None,
        qdrant: httpx.Client | None = None,
    ) -> None:
        self._settings = settings
        self._java = java or managed_client(
            base_url=settings.java_base_url, timeout=settings.java_timeout_seconds
        )
        self._dashscope = dashscope or managed_client(
            base_url=settings.dashscope_base_url, timeout=settings.model_timeout_seconds
        )
        self._qdrant = qdrant or managed_client(
            base_url=settings.qdrant_url, timeout=settings.qdrant_timeout_seconds
        )
        self._owned = (java is None, dashscope is None, qdrant is None)

    def process_once(self, limit: int = 10) -> int:
        jobs = self._claim(limit)
        for job in jobs:
            try:
                if job.operation == "DELETE":
                    self._delete(job)
                elif job.operation == "UPSERT":
                    self._upsert(job)
                else:
                    raise ValueError("unknown index operation")
                self._ack(job, True, None)
            except Exception as error:
                self._ack(job, False, error.__class__.__name__)
        return len(jobs)

    def close(self) -> None:
        for owned, client in zip(self._owned, (self._java, self._dashscope, self._qdrant)):
            if owned:
                client.close()

    def _claim(self, limit: int) -> list[IndexJob]:
        data = self._java_call("POST", "/agent/internal/index/jobs/claim", json={"limit": limit})
        if not isinstance(data, list):
            raise RuntimeError("invalid index claim response")
        return [IndexJob.model_validate(item) for item in data]

    def _ack(self, job: IndexJob, success: bool, error: str | None) -> None:
        self._java_call(
            "POST",
            f"/agent/internal/index/jobs/{job.jobId}/ack",
            json={"leaseToken": job.leaseToken, "success": success, "errorMessage": error},
        )

    def _java_call(self, method: str, path: str, **kwargs):
        token = issue_worker_token(self._settings.service_secret)
        response = self._java.request(
            method, path, headers={"Authorization": f"Bearer {token}"}, **kwargs
        )
        response.raise_for_status()
        body = response.json()
        if not isinstance(body, dict) or body.get("code") != 0:
            raise RuntimeError("Java index gateway rejected request")
        return body.get("data")

    def _upsert(self, job: IndexJob) -> None:
        if not self._settings.dashscope_api_key or not job.scopeKey:
            raise RuntimeError("index embedding is not configured")
        text = self._document(job)
        response = self._dashscope.post(
            "/embeddings",
            headers={"Authorization": f"Bearer {self._settings.dashscope_api_key}"},
            json={"model": self._settings.embedding_model, "input": text,
                  "dimensions": self._settings.embedding_dimensions, "encoding_format": "float"},
        )
        response.raise_for_status()
        vector = response.json()["data"][0]["embedding"]
        if not isinstance(vector, list) or len(vector) != self._settings.embedding_dimensions:
            raise ValueError("embedding dimension mismatch")
        collection = quote(self._settings.qdrant_collection, safe="")
        qdrant = self._qdrant.put(
            f"/collections/{collection}/points",
            params={"wait": "true"}, headers=self._qdrant_headers(),
            json={"points": [{"id": int(job.pictureId), "vector": vector,
                               "payload": {"pictureId": job.pictureId, "scopeKey": job.scopeKey}}]},
        )
        qdrant.raise_for_status()

    def _delete(self, job: IndexJob) -> None:
        collection = quote(self._settings.qdrant_collection, safe="")
        response = self._qdrant.post(
            f"/collections/{collection}/points/delete",
            params={"wait": "true"}, headers=self._qdrant_headers(),
            json={"points": [int(job.pictureId)]},
        )
        response.raise_for_status()

    def _qdrant_headers(self) -> dict[str, str]:
        return {"api-key": self._settings.qdrant_api_key} if self._settings.qdrant_api_key else {}

    @staticmethod
    def _document(job: IndexJob) -> str:
        values = [job.name, job.introduction, job.category]
        if job.tags:
            try:
                tags = json.loads(job.tags)
                if isinstance(tags, list):
                    values.extend(str(tag) for tag in tags if isinstance(tag, str))
            except ValueError:
                pass
        return "\n".join(" ".join(value.split()) for value in values if value and value.strip())[:4000]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run LabVision picture index worker")
    parser.add_argument("--once", action="store_true", help="process one batch and exit")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--poll-seconds", type=float, default=2.0)
    args = parser.parse_args()
    if not 1 <= args.limit <= 20 or args.poll_seconds < 0.1:
        parser.error("limit must be 1..20 and poll-seconds must be >= 0.1")
    worker = PictureIndexWorker(Settings.from_env())
    try:
        while True:
            count = worker.process_once(args.limit)
            if args.once:
                break
            if count == 0:
                time.sleep(args.poll_seconds)
    finally:
        worker.close()


if __name__ == "__main__":
    main()
