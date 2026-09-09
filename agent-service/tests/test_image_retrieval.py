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

    def test_builds_scoped_symmetric_similarity_matrix_from_selected_ids_only(self):
        settings = Settings(
            "http://java", "x" * 32, 10, "dash-key", "https://dash/v1",
            "qwen-plus", 20, "text-embedding-v4", 3,
            "http://qdrant", "q-key", "pictures", 5,
        )
        requests = []

        def handler(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            requests.append(body)
            points = {
                2: [
                    {"score": 0.8, "payload": {"pictureId": "9"}},
                    {"score": 0.99, "payload": {"pictureId": "999"}},
                ],
                9: [
                    {"score": 0.6, "payload": {"pictureId": "2"}},
                    {"score": 0.4, "payload": {"pictureId": "12"}},
                ],
                12: [{"score": 0.2, "payload": {"pictureId": "9"}}],
            }
            return httpx.Response(200, json={"result": {"points": points[body["query"]]}})

        qdrant = httpx.Client(
            base_url="http://qdrant", transport=httpx.MockTransport(handler)
        )
        matrix = SemanticRetriever(
            settings, qdrant_client=qdrant
        ).picture_similarity_matrix(["2", "9", "12"], "space:7")

        self.assertEqual(matrix.picture_ids, ["2", "9", "12"])
        self.assertEqual(len(requests), 3)
        self.assertEqual(matrix.scores[0][0], 1.0)
        self.assertAlmostEqual(matrix.scores[0][1], 0.7)
        self.assertAlmostEqual(matrix.scores[1][0], 0.7)
        self.assertIsNone(matrix.scores[0][2])
        self.assertAlmostEqual(matrix.scores[1][2], 0.3)
        for body in requests:
            self.assertEqual(body["using"], "image_dense")
            self.assertEqual(body["limit"], 2)
            self.assertIn(
                {"key": "scopeKey", "match": {"value": "space:7"}},
                body["filter"]["must"],
            )
            self.assertIn(
                {"key": "pictureId", "match": {"any": ["2", "9", "12"]}},
                body["filter"]["must"],
            )
            self.assertEqual(
                body["filter"]["must_not"],
                [{"key": "pictureId", "match": {"value": str(body["query"])}}],
            )

    def test_rejects_invalid_similarity_request_before_query(self):
        settings = Settings(
            "http://java", "x" * 32, 10, "", "https://dash/v1",
            "qwen-plus", 20, "text-embedding-v4", 3,
            "http://qdrant", "", "pictures", 5,
        )
        retriever = SemanticRetriever(settings)

        invalid_requests = [
            (["2"], "space:7"),
            (["2", "2"], "space:7"),
            (["0", "2"], "space:7"),
            (["2", "9223372036854775808"], "space:7"),
            (["2", "9"], "space:0"),
            (["2", "9"], "private:7"),
        ]
        for picture_ids, scope_key in invalid_requests:
            with self.subTest(picture_ids=picture_ids, scope_key=scope_key):
                with self.assertRaises(ValueError):
                    retriever.picture_similarity_matrix(picture_ids, scope_key)

    def test_rejects_out_of_range_qdrant_similarity_score(self):
        settings = Settings(
            "http://java", "x" * 32, 10, "", "https://dash/v1",
            "qwen-plus", 20, "text-embedding-v4", 3,
            "http://qdrant", "", "pictures", 5,
        )

        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"result": {"points": [
                {"score": 1.01, "payload": {"pictureId": "9"}},
            ]}})

        qdrant = httpx.Client(
            base_url="http://qdrant", transport=httpx.MockTransport(handler)
        )
        with self.assertRaisesRegex(ValueError, "similarity score"):
            SemanticRetriever(
                settings, qdrant_client=qdrant
            ).picture_similarity_matrix(["2", "9"], "public")


if __name__ == "__main__":
    unittest.main()
