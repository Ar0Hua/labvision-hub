import unittest
from types import SimpleNamespace
from pydantic import ValidationError
from app.retrieval.intent import SearchIntent, IntentParser
from app.retrieval.semantic import SemanticRetriever
from app.retrieval.keyword_executor import KeywordSearchExecutor
from app.runtime.java_client import PictureCandidate, TaskContext


class AspectFilterTests(unittest.TestCase):
    def test_bounds_and_multiturn(self):
        for args in ({"minAspectRatio": 0}, {"maxAspectRatio": float("nan")},
                     {"maxAspectRatio": 101}, {"minAspectRatio": 2, "maxAspectRatio": 1}):
            with self.assertRaises(ValidationError):
                SearchIntent(searchText="图", **args)
        previous = SearchIntent(searchText="图", minAspectRatio=1.5).model_dump(mode="json")
        self.assertEqual(IntentParser._fallback("更高清", previous).minAspectRatio, 1.5)
        self.assertIsNone(IntentParser._fallback("重置", previous).minAspectRatio)

    def test_vector_range_keeps_permission_scope(self):
        must = SemanticRetriever._filter("space:9", {"minAspectRatio": 1.5, "maxAspectRatio": 2})["must"]
        self.assertIn({"key": "aspectRatio", "range": {"gte": 1.5, "lte": 2}}, must)
        self.assertIn({"key": "scopeKey", "match": {"value": "space:9"}}, must)

    def test_final_metadata_filter_and_boundary(self):
        parser = SimpleNamespace(parse=lambda *_: SearchIntent(searchText="图", minAspectRatio=1.5, maxAspectRatio=2))
        values = [PictureCandidate(pictureId=str(i), spaceId="9", width=w, height=h)
                  for i, w, h in [(1, 150, 100), (2, 200, 100), (3, 201, 100), (4, 10, 0), (5, None, None)]]
        calls = []
        context = TaskContext(taskId="task", conversationId="conversation", userId="7", spaceId="9", query="图", status="RUNNING")
        result = KeywordSearchExecutor(parser).execute(context,
            lambda *args: calls.append(args[4]) or values, lambda ids: values, lambda: None)
        self.assertEqual([c["pictureId"] for c in result.citations], ["1", "2"])
        self.assertEqual(calls[0]["minAspectRatio"], 1.5)
