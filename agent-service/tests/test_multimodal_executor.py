import unittest

from app.config import Settings
from app.retrieval.intent import IntentParser
from app.retrieval.keyword_executor import KeywordSearchExecutor
from app.runtime.java_client import PictureCandidate, TaskContext


class MultimodalExecutorTests(unittest.TestCase):
    def test_fuses_authorized_image_candidates(self):
        class Semantic:
            enabled = True

            def search(self, _text, _scope, _limit):
                return []

            def search_by_pictures(self, picture_ids, scope, limit):
                self.image_call = (picture_ids, scope, limit)
                return ["22"]

        settings = Settings(
            "http://java", "x" * 32, 10, "", "https://dash/v1", "qwen-plus", 20,
            "text-embedding-v4", 3, "http://qdrant", "", "pictures", 5)
        semantic = Semantic()
        context = TaskContext(
            taskId="task", conversationId="conversation", userId="7", spaceId="9",
            query="寻找同类荧光图", examplePictureIds=["11"], status="RUNNING")
        candidate = PictureCandidate(pictureId="22", spaceId="9", name="候选图")

        result = KeywordSearchExecutor(IntentParser(settings), semantic).execute(
            context, lambda *_: [], lambda ids: [candidate] if ids == ["22"] else [],
            lambda: None)

        self.assertEqual(semantic.image_call, (["11"], "space:9", 20))
        self.assertEqual(result.citations[0]["pictureId"], "22")


if __name__ == "__main__":
    unittest.main()
