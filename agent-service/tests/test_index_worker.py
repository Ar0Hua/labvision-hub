import json
from io import BytesIO
from PIL import Image
import unittest

import httpx

from app.config import Settings
from app.indexing.worker import PictureIndexWorker


def settings() -> Settings:
    return Settings("http://java/api", "x" * 32, 10, "dash-key", "https://dash/v1",
                    "qwen-plus", 20, "text-embedding-v4", 3,
                    "http://qdrant", "q-key", "pictures", 5,
                    image_embedding_dimensions=3)


class IndexWorkerTests(unittest.TestCase):
    def test_upsert_embeds_writes_qdrant_then_acknowledges(self):
        acknowledgements = []

        def java_handler(request: httpx.Request) -> httpx.Response:
            if request.url.path.endswith("/claim"):
                data = [{"jobId": "11", "leaseToken": "lease", "pictureId": "2059881449783808001",
                         "operation": "UPSERT", "scopeKey": "space:9", "spaceId": "9",
                         "reviewStatus": 1, "name": "显微图", "introduction": "细胞",
                         "category": "显微成像", "tags": '["荧光"]',
                         "sourceUpdatedAtEpoch": 123, "temporaryUrl": "https://cos/image.png"}]
            else:
                acknowledgements.append(json.loads(request.content)); data = True
            self.assertTrue(request.headers["authorization"].startswith("Bearer "))
            return httpx.Response(200, json={"code": 0, "data": data})

        java = httpx.Client(base_url="http://java/api", transport=httpx.MockTransport(java_handler))
        def dash_handler(request: httpx.Request) -> httpx.Response:
            if request.url.path.endswith("/chat/completions"):
                return httpx.Response(200, json={"choices": [{"message": {
                    "content": '{"caption":"细胞荧光图","ocrText":"S1"}'}}]})
            return httpx.Response(200, json={"data": [{"embedding": [0.1, 0.2, 0.3]}]})

        dash = httpx.Client(base_url="https://dash/v1",
                            transport=httpx.MockTransport(dash_handler))
        qdrant_requests = []
        qdrant = httpx.Client(base_url="http://qdrant", transport=httpx.MockTransport(
            lambda request: (qdrant_requests.append(request) or httpx.Response(200, json={"status": "ok"}))
        ))
        output = BytesIO()
        Image.new("RGB", (16, 16), color="green").save(output, format="PNG")
        png = output.getvalue()
        image = httpx.Client(transport=httpx.MockTransport(
            lambda _request: httpx.Response(200, content=png, headers={"content-type": "image/png"})))
        multimodal = httpx.Client(base_url="https://multi", transport=httpx.MockTransport(
            lambda _request: httpx.Response(200, json={"output": {"embeddings": [
                {"embedding": [0.4, 0.5, 0.6]}]}})))
        worker = PictureIndexWorker(settings(), java, dash, qdrant, image, multimodal)
        self.assertEqual(worker.process_once(), 1)
        point = json.loads(qdrant_requests[0].content)["points"][0]
        self.assertEqual(point["payload"]["pictureId"], "2059881449783808001")
        self.assertEqual(point["payload"]["scopeKey"], "space:9")
        self.assertEqual(point["vector"]["text_dense"], [0.1, 0.2, 0.3])
        self.assertEqual(point["vector"]["image_dense"], [0.4, 0.5, 0.6])
        self.assertTrue(acknowledgements[0]["success"])
        self.assertEqual(acknowledgements[0]["caption"], "细胞荧光图")

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
