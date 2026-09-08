import json
import unittest

import httpx

from app.config import Settings
from app.retrieval.semantic import SemanticRetriever


class ImageRetrievalTests(unittest.TestCase):
    def test_queries_named_image_vector_with_scope_and_excludes_examples(self):
        settings = Settings(
            "http://java", "x" * 32, 10, "dash-key", "https://dash/v1",
            "qwen-plus", 20, "text-embedding-v4", 3,
            "http://qdrant", "q-key", "pictures", 5,
        )
        requests = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(200, json={"result": {"points": [
                {"payload": {"pictureId": "9"}},
                {"payload": {"pictureId": "2"}},
            ]}})

        qdrant = httpx.Client(base_url="http://qdrant",
                              transport=httpx.MockTransport(handler))
        result = SemanticRetriever(settings, qdrant_client=qdrant).search_by_pictures(
            ["2"], "space:7", 10, {"formats": ["tif"]})

        self.assertEqual(result, ["9"])
        body = json.loads(requests[0].content)
        self.assertEqual(body["query"], 2)
        self.assertEqual(body["using"], "image_dense")
        self.assertEqual(body["filter"]["must"][0]["match"]["value"], "space:7")
        self.assertEqual(body["filter"]["must_not"][0]["match"]["any"], ["2"])

        self.assertIn({"key": "picFormat", "match": {"any": ["tif"]}}, body["filter"]["must"])

if __name__ == "__main__":
    unittest.main()
