import json
import unittest

import httpx
from pydantic import ValidationError

from app.config import Settings
from app.retrieval.intent import IntentParser, SearchIntent
from app.retrieval.keyword_executor import KeywordSearchExecutor
from app.runtime.java_client import JavaTaskClient, TaskContext


def settings() -> Settings:
    return Settings("http://java", "x" * 32, 10, "key", "https://dashscope.example/v1",
                    "qwen-plus", 20, "text-embedding-v4", 1024,
                    "http://qdrant", "", "pictures", 5)


class StructuredFilterTests(unittest.TestCase):
    def test_strict_intent_normalizes_supported_filters(self):
        intent = SearchIntent(
            searchText="断面原始图", formats=[".PNG", "png"], createdAfter="2026-05-01",
            createdBefore="2026-05-31", minWidth=1920, minHeight=1080,
            maxSizeBytes=10_485_760, sort="oldest")
        self.assertEqual(intent.formats, ["png"])
        self.assertEqual(intent.createdAfter.isoformat(), "2026-05-01")
        self.assertEqual(intent.sort, "oldest")
        with self.assertRaises(ValidationError):
            SearchIntent(searchText="图", formats=["svg"])
        with self.assertRaises(ValidationError):
            SearchIntent(searchText="图", createdAfter="2026-06-01",
                         createdBefore="2026-05-01")

    def test_executor_forwards_only_typed_filters(self):
        class Parser:
            def parse(self, _query, _previous=None):
                return SearchIntent(searchText="河道", formats=["jpg"], minWidth=2048,
                                    createdAfter="2026-06-01", sort="newest")

        calls = []
        context = TaskContext(taskId="task", conversationId="conversation", userId="7",
                              spaceId="9", query="六月后的高清 jpg", status="RUNNING")
        KeywordSearchExecutor(Parser()).execute(
            context, lambda *args: calls.append(args) or [], lambda _: [], lambda: None)
        filters = calls[0][4]
        self.assertEqual(filters["formats"], ["jpg"])
        self.assertEqual(filters["createdAfter"], "2026-06-01")
        self.assertEqual(filters["minWidth"], 2048)
        self.assertEqual(filters["sort"], "newest")

    def test_java_client_sends_flat_allowlisted_contract(self):
        seen = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen.append(json.loads(request.content))
            return httpx.Response(200, json={"code": 0, "data": []})

        client = httpx.Client(base_url="http://java", transport=httpx.MockTransport(handler))
        JavaTaskClient(settings(), client).search_pictures(
            "task", "token", search_text="细胞", limit=12,
            filters={"formats": ["tif"], "minHeight": 1024, "sort": "oldest", "rawSql": "DROP"})
        self.assertEqual(seen[0]["formats"], ["tif"])
        self.assertEqual(seen[0]["minHeight"], 1024)
        self.assertEqual(seen[0]["sort"], "oldest")
        self.assertNotIn("rawSql", seen[0])


if __name__ == "__main__":
    unittest.main()
