import unittest
from app.analysis.space_statistics import SpaceStatistics, SpaceStatisticsComposer
from test_space_statistics import summary


class WindowDistributionTests(unittest.TestCase):
    def test_window_evidence_has_own_denominators(self):
        value=summary().model_dump(mode="json")
        value["window"]={"startDate":"2026-01-01","totals":{"count":5,"totalSize":10},
                         "categories":[],"uploaders":[],"trend":[],
                         "tagDistribution":[{"tag":"显微","count":3}],
                         "sizeDistribution":[{"sizeRange":"<1MB","count":5}],
                         "governance":{"totalCount":5,"indexedCount":2,"qualityIssueCount":1,"untaggedCount":2}}
        answer=SpaceStatisticsComposer.compose(SpaceStatistics.model_validate(value))
        self.assertIn("窗口当前索引覆盖：2/5",answer)
        self.assertIn("质量问题候选 1/2",answer)
        self.assertIn("显微 3",answer)
        self.assertIn("不受上述窗口筛选限制",answer)
