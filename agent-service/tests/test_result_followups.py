import json
import unittest

import httpx
from langgraph.checkpoint.memory import InMemorySaver
from pydantic import ValidationError

from app.config import Settings
from app.graph.workflow import LangGraphWorkflow
from app.retrieval.intent import IntentParser, SearchIntent
from app.retrieval.keyword_executor import KeywordSearchExecutor
from app.runtime.java_client import PictureCandidate, TaskContext


def settings() -> Settings:
    return Settings("http://java", "x" * 32, 10, "key", "https://dashscope.example/v1",
                    "qwen-plus", 20, "text-embedding-v4", 1024,
                    "http://qdrant", "", "pictures", 5)


class ResultFollowupTests(unittest.TestCase):
    def test_picture_ids_are_strict_and_previous_results_are_sanitized(self):
        intent = SearchIntent(
            searchText="细胞", examplePictureIds=["22", "22"],
            excludePictureIds=["11", "11"],
        )
        self.assertEqual(intent.examplePictureIds, ["22"])
        self.assertEqual(intent.excludePictureIds, ["11"])
        with self.assertRaises(ValidationError):
            SearchIntent(searchText="细胞", examplePictureIds=["not-an-id"])

        seen = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen.append(json.loads(request.content))
            content = json.dumps({
                "searchText": "细胞", "examplePictureIds": ["22", "999"],
                "excludePictureIds": ["11", "999"],
            }, ensure_ascii=False)
            return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})

        client = httpx.Client(
            base_url="https://dashscope.example/v1",
            transport=httpx.MockTransport(handler),
        )
        parsed = IntentParser(settings(), client).parse(
            "排除第一张，更像第二张", None, ["11", " 22 ", "bad", "22"])
        payload = json.loads(seen[0]["messages"][1]["content"])
        self.assertEqual(payload["previousResultPictureIds"], ["11", "22"])
        self.assertEqual(parsed.examplePictureIds, ["22"])
        self.assertEqual(parsed.excludePictureIds, ["11"])

    def test_workflow_passes_last_results_and_enforces_followup_operations(self):
        class Parser:
            calls = []

            def parse(self, query, previous=None, previous_results=None):
                self.calls.append((previous, previous_results))
                if previous is None:
                    return SearchIntent(searchText=query)
                return SearchIntent(
                    searchText="细胞", examplePictureIds=["22"],
                    excludePictureIds=["11"],
                )

        class Semantic:
            enabled = True
            image_call = None

            def search(self, _text, _scope, _limit, _filters):
                return []

            def search_by_pictures(self, picture_ids, scope, limit, _filters):
                self.image_call = (picture_ids, scope, limit)
                return ["33"]

        pictures = {
            picture_id: PictureCandidate(
                pictureId=picture_id, spaceId="9", name=f"图片{picture_id}")
            for picture_id in ("11", "22", "33")
        }
        search = lambda *_: [pictures["11"], pictures["22"]]
        authorize = lambda ids: [pictures[picture_id] for picture_id in ids]
        parser = Parser()
        semantic = Semantic()
        workflow = LangGraphWorkflow(
            KeywordSearchExecutor(parser, semantic), InMemorySaver())

        workflow.execute(self._context("task-1", "查找细胞图"), search, authorize, lambda: None)
        result = workflow.execute(
            self._context("task-2", "排除第一张，更像第二张"),
            search, authorize, lambda: None,
        )

        self.assertEqual(parser.calls[1][1], ["11", "22"])
        self.assertEqual(semantic.image_call, (["22"], "space:9", 20))
        self.assertNotIn("11", [item["pictureId"] for item in result.citations])
        self.assertIn("33", [item["pictureId"] for item in result.citations])
        self.assertEqual(result.intent_state["excludePictureIds"], ["11"])

    @staticmethod
    def _context(task_id: str, query: str) -> TaskContext:
        return TaskContext(
            taskId=task_id, conversationId="conversation", userId="7",
            spaceId="9", query=query, status="RUNNING",
        )


if __name__ == "__main__":
    unittest.main()
