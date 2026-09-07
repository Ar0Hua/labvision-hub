import json
import unittest

import httpx

from app.config import Settings
from app.indexing.worker import PictureIndexWorker


def settings() -> Settings:
    return Settings("http://java/api", "x" * 32, 10, "dash-key", "https://dash/v1",
                    "qwen-plus", 20, "text-embedding-v4", 3,
                    "http://qdrant", "q-key", "pictures", 5)


class IndexWorkerTests(unittest.TestCase):
    def test_upsert_embeds_writes_qdrant_then_acknowledges(self):
        acknowledgements = []

        def java_handler(request: httpx.Request) -> httpx.Response:
            if request.url.path.endswith("/claim"):
                data = [{"jobId": "11", "leaseToken": "lease", "pictureId": "2059881449783808001",
                         "operation": "UPSERT", "scopeKey": "space:9", "name": "显微图",
                         "introduction": "细胞", "category": "显微成像", "tags": '["荧光"]'}]
            else:
                acknowledgements.append(json.loads(request.content)); data = True
            self.assertTrue(request.headers["authorization"].startswith("Bearer "))
            return httpx.Response(200, json={"code": 0, "data": data})

        java = httpx.Client(base_url="http://java/api", transport=httpx.MockTransport(java_handler))
        dash = httpx.Client(base_url="https://dash/v1", transport=httpx.MockTransport(
            lambda _request: httpx.Response(200, json={"data": [{"embedding": [0.1, 0.2, 0.3]}]})
        ))
        qdrant_requests = []
        qdrant = httpx.Client(base_url="http://qdrant", transport=httpx.MockTransport(
            lambda request: (qdrant_requests.append(request) or httpx.Response(200, json={"status": "ok"}))
        ))
        worker = PictureIndexWorker(settings(), java, dash, qdrant)
        self.assertEqual(worker.process_once(), 1)
        point = json.loads(qdrant_requests[0].content)["points"][0]
        self.assertEqual(point["payload"]["pictureId"], "2059881449783808001")
        self.assertEqual(point["payload"]["scopeKey"], "space:9")
        self.assertTrue(acknowledgements[0]["success"])

    def test_qdrant_failure_is_acknowledged_for_retry(self):
        acknowledgements = []

        def java_handler(request: httpx.Request) -> httpx.Response:
            if request.url.path.endswith("/claim"):
                data = [{"jobId": "12", "leaseToken": "lease", "pictureId": "7",
                         "operation": "DELETE"}]
            else:
                acknowledgements.append(json.loads(request.content)); data = True
            return httpx.Response(200, json={"code": 0, "data": data})

        java = httpx.Client(base_url="http://java", transport=httpx.MockTransport(java_handler))
        qdrant = httpx.Client(base_url="http://qdrant", transport=httpx.MockTransport(
            lambda _request: httpx.Response(503)
        ))
        dash = httpx.Client(base_url="https://dash")
        PictureIndexWorker(settings(), java, dash, qdrant).process_once()
        self.assertFalse(acknowledgements[0]["success"])
        self.assertEqual(acknowledgements[0]["errorMessage"], "HTTPStatusError")


if __name__ == "__main__":
    unittest.main()
