import unittest
from pydantic import ValidationError
from app.analysis.space_statistics import Governance, SpaceStatistics, SpaceStatisticsComposer


class GovernanceTests(unittest.TestCase):
    def test_reports_coverage_and_unknown_features(self):
        summary = SpaceStatistics.model_validate({
            "scope": {"type": "space", "spaceId": "1"},
            "capturedAt": "2026-09-09T00:00:00Z",
            "usage": {"usedSize": 0, "usedCount": 10},
            "categoryDistribution": [], "tagDistribution": [], "sizeDistribution": [],
            "monthlyUploadTrend": [], "distributionLimit": 20, "trendLimit": 24,
            "governance": {"totalCount": 10, "indexedCount": 2, "qualityIssueCount": 1}
        })
        answer = SpaceStatisticsComposer.compose(summary)
        self.assertIn("索引覆盖：2/10", answer)
        self.assertIn("质量问题候选：1/2", answer)
        with self.assertRaises(ValidationError):
            Governance(indexedCount=-1)
