import json
import unittest
from types import SimpleNamespace

import httpx
from pydantic import ValidationError
from app.retrieval.intent import IntentParser, SearchIntent
from app.retrieval.keyword_executor import KeywordSearchExecutor
from app.retrieval.semantic import SemanticRetriever
from app.runtime.java_client import JavaTaskClient, PictureCandidate, TaskContext
from test_structured_filters import settings


class UploaderFilterTests(unittest.TestCase):
    def test_strict_id_and_multiturn_fallback(self):
        for value in ("0", "-1", "01", "1 OR 1=1", "9223372036854775808", 123):
            with self.assertRaises(ValidationError):
                SearchIntent(searchText="图", uploaderId=value)
        previous = SearchIntent(searchText="图", uploaderId="2059881449783808001").model_dump(mode="json")
        self.assertEqual(IntentParser._fallback("只看高清", previous).uploaderId, previous["uploaderId"])
        self.assertIsNone(IntentParser._fallback("重置", previous).uploaderId)

    def test_vector_filter_keeps_scope_and_review_constraints(self):
        must = SemanticRetriever._filter("public", {"uploaderId": "42"})["must"]
        self.assertIn({"key": "userId", "match": {"value": "42"}}, must)
        self.assertIn({"key": "scopeKey", "match": {"value": "public"}}, must)
        self.assertIn({"key": "reviewStatus", "match": {"value": 1}}, must)

    def test_java_contract_preserves_string_id(self):
        seen = []
        def handler(request):
            seen.append(json.loads(request.content))
            return httpx.Response(200, json={"code": 0, "data": []})
        with httpx.Client(base_url="http://java", transport=httpx.MockTransport(handler)) as client:
            JavaTaskClient(settings(), client).search_pictures("task", "token", search_text="图",
                filters={"uploaderId": "2059881449783808001"})
        self.assertEqual(seen[0]["uploaderId"], "2059881449783808001")

    def test_executor_forwards_filter_and_rechecks_current_uploader(self):
        parser = SimpleNamespace(parse=lambda *_: SearchIntent(searchText="图", uploaderId="42"))
        values = [PictureCandidate(pictureId=str(i), spaceId="9", uploaderId=u)
                  for i, u in ((1, "42"), (2, "43"), (3, None))]
        calls = []
        context = TaskContext(taskId="task", conversationId="conversation", userId="7",
                              spaceId="9", query="上传人ID42", status="RUNNING")
        result = KeywordSearchExecutor(parser).execute(context,
            lambda *args: calls.append(args[4]) or values, lambda ids: values, lambda: None)
        self.assertEqual(calls[0]["uploaderId"], "42")
        self.assertEqual([c["pictureId"] for c in result.citations], ["1"])
