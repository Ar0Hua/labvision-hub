import json
import unittest

from app.analysis.group_analysis import PictureGroupAnalyzer
from app.runtime.java_client import PictureCandidate, TaskContext
from app.runtime.runner import TaskRunner
from app.security.service_token import ServiceContext


def pictures() -> list[PictureCandidate]:
    return [
        PictureCandidate(
            pictureId="11", spaceId="9", name="细胞横图", category="显微成像",
            tags='["荧光染色","细胞培养"]', width=1920, height=1080,
            size=2_097_152, format="PNG"),
        PictureCandidate(
            pictureId="22", spaceId="9", name="细胞方图", category="显微成像",
            tags='["荧光染色","实验记录"]', width=2048, height=2048,
            size=4_194_304, format="png"),
        PictureCandidate(
            pictureId="33", spaceId="9", name="仪器截图", category="仪器记录",
            tags='["荧光染色"]', width=1080, height=1920,
            size=1_048_576, format="jpg"),
    ]


class PictureGroupAnalyzerTests(unittest.TestCase):
    def test_compares_authorized_metadata_and_marks_inference_boundary(self):
        result = PictureGroupAnalyzer.analyze(pictures())

        self.assertTrue(PictureGroupAnalyzer.matches("比较这些图片的差异", ["11", "22"]))
        self.assertFalse(PictureGroupAnalyzer.matches("找相似图片", ["11", "22"]))
        self.assertFalse(PictureGroupAnalyzer.matches("比较这张图片", ["11"]))
        self.assertEqual(result.picture_count, 3)
        self.assertIn("png 2 张", result.answer)
        self.assertIn("显微成像 2 张", result.answer)
        self.assertIn("横向 1 张", result.answer)
        self.assertIn("共同标签：荧光染色", result.answer)
        self.assertIn("不代表视觉质量或实验价值", result.answer)
        self.assertIn("当前结果不作推断", result.answer)
        self.assertEqual(
            [citation["pictureId"] for citation in result.citations],
            ["11", "22", "33"],
        )
        with self.assertRaises(ValueError):
            PictureGroupAnalyzer.analyze(pictures()[:1])

    def test_runner_reauthorizes_selected_pictures_and_skips_search(self):
        class Java:
            events = []
            states = []
            authorized_ids = None

            def get_context(self, _task_id, _token):
                status = "PENDING" if not self.states else "RUNNING"
                return TaskContext(
                    taskId="task", conversationId="conversation", userId="7",
                    spaceId="9", query="对比这些图片的格式和分辨率",
                    examplePictureIds=["11", "22"], status=status)

            def update_state(self, _task_id, _token, **values):
                self.states.append(values)

            def append_event(self, _task_id, _token, event_type, payload):
                self.events.append((event_type, json.loads(payload)))

            def authorize_pictures(self, _task_id, _token, ids):
                self.authorized_ids = ids
                return pictures()[:2]

            def close(self):
                pass

        class Executor:
            def execute(self, *_args):
                raise AssertionError("group comparison must not run picture retrieval")

        java = Java()
        signed = ServiceContext("task", "conversation", "7", "9", 1, 301)
        TaskRunner(java, Executor()).run(signed, "token")

        self.assertEqual(java.authorized_ids, ["11", "22"])
        tools = [payload["tool"] for event, payload in java.events
                 if event in ("tool_start", "tool_result")]
        self.assertEqual(tools, ["picture_group_analysis", "picture_group_analysis"])
        citations = [payload["pictureId"] for event, payload in java.events
                     if event == "citation"]
        self.assertEqual(citations, ["11", "22"])
        self.assertEqual([state["status"] for state in java.states],
                         ["RUNNING", "SUCCEEDED"])


if __name__ == "__main__":
    unittest.main()
