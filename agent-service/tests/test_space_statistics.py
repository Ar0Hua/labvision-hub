import json
import unittest

from pydantic import ValidationError

from app.analysis.space_statistics import SpaceStatistics, SpaceStatisticsComposer
from app.runtime.java_client import TaskContext
from app.runtime.runner import TaskRunner
from app.security.service_token import ServiceContext


def summary() -> SpaceStatistics:
    return SpaceStatistics.model_validate({
        "scope": {"type": "space", "spaceId": "9"},
        "capturedAt": "2026-09-09T00:00:00Z",
        "usage": {
            "usedSize": 1_572_864, "maxSize": 10_485_760, "sizeUsageRatio": 15.0,
            "usedCount": 12, "maxCount": 100, "countUsageRatio": 12.0,
        },
        "categoryDistribution": [
            {"category": "显微成像", "count": 8, "totalSize": 1_000_000}],
        "tagDistribution": [{"tag": "荧光染色", "count": 6}],
        "sizeDistribution": [{"sizeRange": "500KB-1MB", "count": 4}],
        "monthlyUploadTrend": [{"period": "2026-09", "count": 3}],
        "distributionLimit": 20,
        "trendLimit": 24,
    })


class SpaceStatisticsTests(unittest.TestCase):
    def test_contract_and_deterministic_answer_include_scope_time_and_source(self):
        result = SpaceStatisticsComposer.compose(summary())
        self.assertTrue(SpaceStatisticsComposer.matches("这个空间的分类分布和使用率如何"))
        self.assertFalse(SpaceStatisticsComposer.matches("帮我找显微图"))
        self.assertIn("空间 9", result)
        self.assertIn("2026-09-09", result)
        self.assertTrue(SpaceStatisticsComposer.matches("当前空间有多少张图"))
        self.assertFalse(SpaceStatisticsComposer.matches("找文件大小小于 1MB 的图片"))
        self.assertIn("图片数量：12 张", result)
        self.assertIn("显微成像 8 张", result)
        self.assertIn("不是模型估算", result)

        invalid = summary().model_dump(mode="json")
        invalid["unknown"] = True
        with self.assertRaises(ValidationError):
            SpaceStatistics.model_validate(invalid)
        invalid = summary().model_dump(mode="json")
        invalid["tagDistribution"] = [
            {"tag": str(index), "count": 1} for index in range(21)]
        with self.assertRaises(ValidationError):
            SpaceStatistics.model_validate(invalid)

    def test_runner_routes_statistics_without_calling_picture_executor(self):
        invalid = summary().model_dump(mode="json")
        invalid["scope"] = {"type": "public", "spaceId": "9"}
        with self.assertRaises(ValidationError):
            SpaceStatistics.model_validate(invalid)

        class Java:
            events = []
            states = []

            def get_context(self, _task_id, _token):
                status = "PENDING" if not self.states else "RUNNING"
                return TaskContext(
                    taskId="task", conversationId="conversation", userId="7",
                    spaceId="9", query="这个空间有多少图片，容量使用率是多少", status=status)

            def update_state(self, _task_id, _token, **values):
                self.states.append(values)

            def append_event(self, _task_id, _token, event_type, payload):
                self.events.append((event_type, json.loads(payload)))

            def get_space_statistics(self, _task_id, _token):
                return summary()

            def close(self):
                pass

        class Executor:
            def execute(self, *_args):
                raise AssertionError("statistics query must not run picture retrieval")

        java = Java()
        signed = ServiceContext("task", "conversation", "7", "9", 1, 301)
        TaskRunner(java, Executor()).run(signed, "token")

        tools = [payload["tool"] for event, payload in java.events
                 if event in ("tool_start", "tool_result")]
        self.assertEqual(tools, ["space_statistics", "space_statistics"])
        answers = [payload["text"] for event, payload in java.events
                   if event == "answer_delta"]
        self.assertIn("图片数量：12 张", answers[0])
        self.assertEqual([state["status"] for state in java.states],
                         ["RUNNING", "SUCCEEDED"])


if __name__ == "__main__":
    unittest.main()
