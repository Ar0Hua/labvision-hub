import unittest

from langgraph.checkpoint.memory import InMemorySaver

from app.config import Settings
from app.graph.workflow import LangGraphWorkflow
from app.retrieval.intent import IntentParser, SearchIntent
from app.retrieval.keyword_executor import KeywordSearchExecutor
from app.runtime.java_client import TaskContext


def settings() -> Settings:
    return Settings("http://java", "x" * 32, 10, "", "https://dashscope.example/v1",
                    "qwen-plus", 20, "text-embedding-v4", 1024,
                    "http://qdrant", "", "pictures", 5)


class MultiTurnFilterTests(unittest.TestCase):
    def test_model_outage_keeps_previous_filters_and_explicit_reset_clears_them(self):
        parser = IntentParser(settings())
        previous = SearchIntent(
            searchText="河道断面", category="原始数据", formats=["tif"],
            createdAfter="2026-05-01", minWidth=1920,
        ).model_dump(mode="json")

        continued = parser.parse("时间再近一点", previous)
        self.assertEqual(continued.category, "原始数据")
        self.assertEqual(continued.formats, ["tif"])
        self.assertEqual(continued.minWidth, 1920)

        reset = parser.parse("重置，重新找显微图", previous)
        self.assertIsNone(reset.category)
        self.assertEqual(reset.formats, [])
        self.assertIsNone(reset.minWidth)

    def test_checkpoint_passes_validated_intent_to_next_turn(self):
        class Parser:
            calls = []

            def parse(self, query, previous=None):
                self.calls.append(previous)
                if previous is None:
                    return SearchIntent(searchText=query, formats=["png"])
                self.assert_previous(previous)
                return SearchIntent(searchText="细胞", formats=previous["formats"], minWidth=2048)

            @staticmethod
            def assert_previous(previous):
                if previous.get("formats") != ["png"]:
                    raise AssertionError("checkpoint did not restore prior filters")

        parser = Parser()
        workflow = LangGraphWorkflow(KeywordSearchExecutor(parser), InMemorySaver())
        captured = []
        search = lambda *args: captured.append(args[4]) or []
        workflow.execute(self._context("task-1", "查找 png 细胞图"), search,
                         lambda _: [], lambda: None)
        workflow.execute(self._context("task-2", "分辨率再高一点"), search,
                         lambda _: [], lambda: None)

        self.assertIsNone(parser.calls[0])
        self.assertEqual(parser.calls[1]["formats"], ["png"])
        self.assertEqual(captured[1]["formats"], ["png"])
        self.assertEqual(captured[1]["minWidth"], 2048)
        state = workflow.state(self._context("task-2", "ignored"))
        self.assertEqual(state["intent_state"]["minWidth"], 2048)

    @staticmethod
    def _context(task_id: str, query: str) -> TaskContext:
        return TaskContext(taskId=task_id, conversationId="conversation", userId="7",
                           spaceId="9", query=query, status="RUNNING")


if __name__ == "__main__":
    unittest.main()
