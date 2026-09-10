import unittest
from types import SimpleNamespace

from app.retrieval.intent import SearchIntent
from app.retrieval.keyword_executor import KeywordSearchExecutor
from app.retrieval.ordering import order_candidates
from app.runtime.java_client import PictureCandidate, PictureFeatures, TaskContext


def picture(id, date=None, digest=None):
    return PictureCandidate(pictureId=str(id), spaceId="9", createdAt=date,
        features=PictureFeatures(contentHash=digest) if digest else None)


class CandidateOrderingTests(unittest.TestCase):
    def test_timezones_milliseconds_ties_and_missing_dates(self):
        values = [picture(1), picture(2, "invalid"),
                  picture(3, "2026-01-01T08:00:00+08:00"),
                  picture(4, "2026-01-01T00:00:00Z"),
                  picture(5, 0), picture(6, "2026-01-02T00:00:00")]
        self.assertEqual([p.pictureId for p in order_candidates(values, "newest")],
                         ["6", "3", "4", "5", "1", "2"])
        self.assertEqual([p.pictureId for p in order_candidates(values, "oldest")],
                         ["5", "3", "4", "6", "1", "2"])
        self.assertEqual(order_candidates(values, "relevance"), values)
        with self.assertRaises(ValueError):
            order_candidates(values, "invalid")

    def test_sort_before_limit_and_fold_uses_current_authorized_metadata(self):
        values = [picture(1, "2026-01-01", "a"*64),
                  picture(2, "2026-01-02", "a"*64),
                  picture(3, "2026-01-03"), picture(4, "2026-01-04")]
        parser = SimpleNamespace(parse=lambda *_: SearchIntent(searchText="图", sort="newest", limit=2))
        semantic = SimpleNamespace(enabled=True, search=lambda *_: ["1", "2", "3", "4"])
        def authorize(ids):
            return [p.model_copy(update={"createdAt": "2026-02-01"}) if p.pictureId == "2" else p
                    for p in values if p.pictureId in ids and p.pictureId != "4"]
        context = TaskContext(taskId="task", conversationId="conversation", userId="7",
                              spaceId="9", query="图按最新", status="RUNNING")
        result = KeywordSearchExecutor(parser, semantic).execute(
            context, lambda *_: values[:2], authorize, lambda: None)
        self.assertEqual([c["pictureId"] for c in result.citations], ["2", "3"])
        self.assertIn("不代表全库时间排名", result.answer)
        self.assertIn("已折叠 1 项", result.answer)

    def test_final_authorization_is_batched_before_limit(self):
        values = [picture(i, f"2026-01-{i:02d}") for i in range(1, 31)]
        parser = SimpleNamespace(parse=lambda *_: SearchIntent(searchText="图", sort="newest", limit=2))
        semantic = SimpleNamespace(enabled=True, search=lambda *_: [str(i) for i in range(16, 31)])
        batches = []
        def authorize(ids):
            batches.append(len(ids))
            self.assertLessEqual(len(ids), 20)
            return [p for p in values if p.pictureId in ids]
        context = TaskContext(taskId="task", conversationId="conversation", userId="7",
                              spaceId="9", query="最新", status="RUNNING")
        result = KeywordSearchExecutor(parser, semantic).execute(
            context, lambda *_: values[:15], authorize, lambda: None)
        self.assertEqual(batches, [15, 20, 10])
        self.assertEqual([c["pictureId"] for c in result.citations], ["30", "29"])
