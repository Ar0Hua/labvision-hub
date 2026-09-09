import unittest
from app.analysis.space_statistics import SpaceStatisticsComposer
from test_space_statistics import summary


class StatisticsWindowTests(unittest.TestCase):
    def test_filtered_counts_and_whole_scope_are_not_conflated(self):
        value = summary().model_dump()
        value["window"] = {
            "startDate": "2026-05-01", "endDate": "2026-05-31", "uploaderId": "7",
            "totals": {"count": 2, "totalSize": 100}, "categories": [],
            "uploaders": [{"uploaderId": "7", "count": 2}],
            "trend": [{"period": "2026-05", "count": 2}]
        }
        answer = SpaceStatisticsComposer.compose(type(summary()).model_validate(value))
        self.assertIn("窗口图片数量：2", answer)
        self.assertIn("全空间快照，不受上述窗口筛选限制", answer)
        self.assertIn("图片数量：12", answer)
