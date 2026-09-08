import unittest

from app.retrieval.keyword_executor import KeywordSearchExecutor
from app.retrieval.intent import IntentParser
from app.config import Settings
from app.runtime.java_client import PictureCandidate, TaskContext


class KeywordExecutorTests(unittest.TestCase):
    def setUp(self):
        self.context = TaskContext(
            taskId="task", conversationId="conversation", userId="7", spaceId="9",
            query="显微 成像", status="RUNNING"
        )

    def test_formats_permission_scoped_results_and_citations(self):
        calls = []

        def search(text, category, tags, limit, filters):
            calls.append((text, category, tags, limit, filters))
            return [PictureCandidate(
                pictureId="2059881449783808001", spaceId="9", name="细胞显微图",
                category="显微成像", tags='["细胞培养","荧光染色"]'
            )]

        result = KeywordSearchExecutor(IntentParser(self._settings())).execute(
            self.context, search, lambda ids: [], lambda: None
        )
        self.assertEqual(calls[0][:4], ("显微 成像", None, [], 10))
        self.assertEqual(calls[0][4]["formats"], [])
        self.assertEqual(calls[0][4]["sort"], "relevance")
        self.assertIn("2059881449783808001", result.answer)
        self.assertIn("细胞培养", result.answer)
        self.assertEqual(result.citations[0]["pictureId"], "2059881449783808001")

    def test_empty_result_is_explicit_and_has_no_citation(self):
        result = KeywordSearchExecutor(IntentParser(self._settings())).execute(
            self.context, lambda *_: [], lambda ids: [], lambda: None
        )
        self.assertEqual(result.candidate_count, 0)
        self.assertEqual(result.citations, [])
        self.assertIn("没有找到", result.answer)

    def test_authorized_vector_candidates_are_fused_with_keyword_results(self):
        class Semantic:
            enabled = True
            def search(self, text, scope_key, limit, _filters):
                self.call = (text, scope_key, limit)
                return ["2", "3"]

        semantic = Semantic()
        keyword = [
            PictureCandidate(pictureId="1", spaceId="9", name="关键词一"),
            PictureCandidate(pictureId="2", spaceId="9", name="共同结果"),
        ]
        authorized = [
            PictureCandidate(pictureId="2", spaceId="9", name="共同结果"),
            PictureCandidate(pictureId="3", spaceId="9", name="向量结果"),
        ]
        result = KeywordSearchExecutor(IntentParser(self._settings()), semantic).execute(
            self.context,
            lambda *_: keyword,
            lambda ids: authorized if ids == ["2", "3"] else [],
            lambda: None,
        )
        self.assertEqual(result.citations[0]["pictureId"], "2")
        self.assertEqual(semantic.call[1], "space:9")

    def _settings(self):
        return Settings("http://java", "x" * 32, 10, "", "https://dashscope.example/v1",
                        "qwen-plus", 20, "text-embedding-v4", 1024,
                        "http://qdrant", "", "pictures", 5)


if __name__ == "__main__":
    unittest.main()
