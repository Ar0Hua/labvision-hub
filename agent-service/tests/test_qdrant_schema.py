import unittest

import httpx

from app.config import Settings
from app.indexing.qdrant_schema import QdrantSchemaError, QdrantSchemaManager


def settings() -> Settings:
    return Settings("http://java", "x" * 32, 10, "", "https://dashscope.example/v1",
                    "qwen-plus", 20, "text-embedding-v4", 1024,
                    "http://qdrant", "secret", "labvision_picture_v1", 5)


class QdrantSchemaTests(unittest.TestCase):
    def test_creates_collection_and_keyword_payload_indexes(self):
        requests = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            if request.method == "GET":
                return httpx.Response(404)
            return httpx.Response(200, json={"status": "ok"})

        client = httpx.Client(base_url="http://qdrant", transport=httpx.MockTransport(handler))
        QdrantSchemaManager(settings(), client).ensure()
        self.assertEqual([(r.method, r.url.path) for r in requests], [
            ("GET", "/collections/labvision_picture_v1"),
            ("PUT", "/collections/labvision_picture_v1"),
            ("PUT", "/collections/labvision_picture_v1/index"),
            ("PUT", "/collections/labvision_picture_v1/index"),
        ])
        self.assertTrue(all(r.headers["api-key"] == "secret" for r in requests))

    def test_existing_compatible_schema_is_idempotent(self):
        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "GET":
                return httpx.Response(200, json={"result": {"config": {"params": {"vectors": {
                    "size": 1024, "distance": "Cosine"
                }}}}})
            return httpx.Response(200, json={"status": "ok"})

        client = httpx.Client(base_url="http://qdrant", transport=httpx.MockTransport(handler))
        QdrantSchemaManager(settings(), client).ensure()

    def test_incompatible_existing_schema_is_not_modified(self):
        client = httpx.Client(base_url="http://qdrant", transport=httpx.MockTransport(
            lambda _request: httpx.Response(200, json={"result": {"config": {"params": {"vectors": {
                "size": 768, "distance": "Cosine"
            }}}}})
        ))
        with self.assertRaises(QdrantSchemaError):
            QdrantSchemaManager(settings(), client).ensure()


if __name__ == "__main__":
    unittest.main()
