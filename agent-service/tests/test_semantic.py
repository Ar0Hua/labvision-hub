import json
import unittest

import httpx

from app.config import Settings
from app.retrieval.semantic import SemanticRetriever


def settings(api_key: str = "dash-key") -> Settings:
    return Settings("http://java", "x" * 32, 10, api_key, "https://dashscope.example/v1",
                    "qwen-plus", 20, "text-embedding-v4", 3,
                    "http://qdrant", "qdrant-key", "pictures/v1", 5)


class SemanticRetrieverTests(unittest.TestCase):
    def test_embedding_and_qdrant_scope_filter(self):
        embedding = httpx.Client(base_url="https://dashscope.example/v1", transport=httpx.MockTransport(
            lambda _request: httpx.Response(200, json={"data": [{"embedding": [0.1, 0.2, 0.3]}]})
        ))
        requests = []

        def qdrant_handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(200, json={"result": {"points": [
                {"payload": {"pictureId": "2059881449783808001"}},
                {"payload": {"pictureId": 2059881449783808002}},
            ]}})

        qdrant = httpx.Client(base_url="http://qdrant", transport=httpx.MockTransport(qdrant_handler))
        filters = {
            "formats": ["png"], "minWidth": 1920, "createdAfter": "2026-05-01",
            "excludePictureIds": ["7"],
        }
        ids = SemanticRetriever(settings(), embedding, qdrant).search(
            "细胞", "space:9", 10, filters)
        self.assertEqual(ids, ["2059881449783808001"])
        body = json.loads(requests[0].content)
        must = body["filter"]["must"]
        self.assertIn({"key": "picFormat", "match": {"any": ["png"]}}, must)
        self.assertIn({"key": "picWidth", "range": {"gte": 1920}}, must)
        self.assertTrue(any(item.get("key") == "createdAtEpoch" for item in must))
        self.assertEqual(body["filter"]["must"][0]["match"]["value"], "space:9")
        self.assertEqual(body["filter"]["must_not"][0]["match"]["any"], ["7"])
        self.assertEqual(requests[0].headers["api-key"], "qdrant-key")
        self.assertIn("pictures%2Fv1", str(requests[0].url))

    def test_missing_dashscope_key_disables_vector_channel(self):
        retriever = SemanticRetriever(settings(""))
        self.assertFalse(retriever.enabled)
        self.assertEqual(retriever.search("细胞", "public"), [])


if __name__ == "__main__":
    unittest.main()
