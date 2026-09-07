import unittest

from app.retrieval.keyword_executor import KeywordSearchExecutor
from app.retrieval.intent import IntentParser
from app.config import Settings
from app.runtime.java_client import PictureCandidate, TaskContext


class KeywordExecutorTests(unittest.TestCase):
    def setUp(self):
        self.context = TaskContext(
            taskId="task", conversationId="conversation", userId="7", spaceId="9", query="显微 成像"
        )

    def test_formats_permission_scoped_results_and_citations(self):
        calls = []

        def search(text, category, tags, limit):
            calls.append((text, category, tags, limit))
            return [PictureCandidate(
                pictureId="2059881449783808001", spaceId="9", name="细胞显微图",
                category="显微成像", tags='["细胞培养","荧光染色"]'
            )]

        result = KeywordSearchExecutor(IntentParser(self._settings())).execute(self.context, search)
        self.assertEqual(calls, [("显微 成像", None, [], 10)])
        self.assertIn("2059881449783808001", result.answer)
        self.assertIn("细胞培养", result.answer)
        self.assertEqual(result.citations[0]["pictureId"], "2059881449783808001")

    def test_empty_result_is_explicit_and_has_no_citation(self):
        result = KeywordSearchExecutor(IntentParser(self._settings())).execute(
            self.context, lambda _text, _category, _tags, _limit: []
        )
        self.assertEqual(result.candidate_count, 0)
        self.assertEqual(result.citations, [])
        self.assertIn("没有找到", result.answer)

    def _settings(self):
        return Settings("http://java", "x" * 32, 10, "", "https://dashscope.example/v1",
                        "qwen-plus", 20, "http://qdrant", "pictures")


if __name__ == "__main__":
    unittest.main()
