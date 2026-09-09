import json
import unittest

from app.analysis.group_analysis import PictureGroupAnalyzer
from app.retrieval.keyword_executor import ExecutionResult
from app.retrieval.semantic import PictureSimilarityMatrix
from app.runtime.java_client import PictureCandidate, TaskContext, VisionInput
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

    def test_composes_similarity_matrix_pair_and_vector_representative(self):
        matrix = PictureSimilarityMatrix(
            ["11", "22", "33"],
            [
                [1.0, 0.9, 0.2],
                [0.9, 1.0, 0.4],
                [0.2, 0.4, 1.0],
            ],
        )

        result = PictureGroupAnalyzer.analyze_similarity(pictures(), matrix)

        self.assertEqual(result.known_pair_count, 3)
        self.assertEqual(result.total_pair_count, 3)
        self.assertIn("覆盖 3/3 对", result.answer)
        self.assertIn("| 11 | 1.000 | 0.900 | 0.200 |", result.answer)
        self.assertIn("细胞横图 [图片 ID: 11] 与 细胞方图 [图片 ID: 22]", result.answer)
        self.assertIn("向量中心代表项：细胞方图 [图片 ID: 22]", result.answer)
        self.assertIn("不代表视觉质量、实验价值或科研结论", result.answer)

    def test_runner_reauthorizes_selected_pictures_and_skips_search(self):
        class Java:
            events = []
            states = []
            authorized_ids = None
            vision_ids = None

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

            def get_vision_inputs(self, _task_id, _token, ids):
                self.vision_ids = ids
                picture = pictures()[0]
                return [VisionInput(
                    **picture.model_dump(),
                    temporaryUrl="https://signed.example/11?token=short",
                    expiresInSeconds=120,
                )]


            def close(self):
                pass

        class Executor:
            def execute(self, *_args):
                raise AssertionError("group comparison must not run picture retrieval")

        class Semantic:
            picture_ids = None
            scope_key = None

            def picture_similarity_matrix(self, picture_ids, scope_key):
                self.picture_ids = picture_ids
                self.scope_key = scope_key
                return PictureSimilarityMatrix(
                    ["11", "22"], [[1.0, 0.91], [0.91, 1.0]]
                )

        class Vision:
            enabled = True
            max_pictures = 1

            def analyze(self, _query, selected):
                self.selected = selected
                return "第一张为横向画面。"

        java = Java()
        signed = ServiceContext("task", "conversation", "7", "9", 1, 301)
        vision = Vision()
        semantic = Semantic()
        TaskRunner(java, Executor(), vision, semantic=semantic).run(signed, "token")

        self.assertEqual(java.authorized_ids, ["11", "22"])
        self.assertEqual(semantic.picture_ids, ["11", "22"])
        self.assertEqual(semantic.scope_key, "space:9")
        tools = [payload["tool"] for event, payload in java.events
                 if event in ("tool_start", "tool_result")]
        self.assertEqual(tools, [
            "picture_group_analysis", "picture_group_analysis",
            "picture_group_similarity", "picture_group_similarity",
            "vision_analysis", "vision_analysis",
        ])
        citations = [payload["pictureId"] for event, payload in java.events
                     if event == "citation"]
        self.assertEqual(citations, ["11", "22"])
        self.assertEqual([state["status"] for state in java.states],
                         ["RUNNING", "SUCCEEDED"])

        self.assertEqual(java.vision_ids, ["11"])
        answers = [payload["text"] for event, payload in java.events
                   if event == "answer_delta"]
        self.assertIn("视觉模型观察（覆盖 1/2 张", answers[0])
        self.assertIn("第一张为横向画面", answers[0])
        self.assertIn("图像向量相似度证据（覆盖 1/1 对", answers[0])
        self.assertIn("向量中心代表项：细胞横图 [图片 ID: 11]", answers[0])

    def test_similarity_failure_keeps_deterministic_group_answer(self):
        class Java:
            events = []

            def append_event(self, _task_id, _token, event_type, payload):
                self.events.append((event_type, json.loads(payload)))

        class FailingSemantic:
            def picture_similarity_matrix(self, _picture_ids, _scope_key):
                raise RuntimeError("qdrant unavailable")

        base = ExecutionResult("元数据结果", [], 2)
        context = TaskContext(
            taskId="task", conversationId="conversation", userId="7",
            spaceId="9", query="对比这些图片", examplePictureIds=["11", "22"],
            status="RUNNING",
        )
        runner = TaskRunner(Java(), object(), semantic=FailingSemantic())
        result = runner._add_group_similarity(
            base, pictures()[:2], context,
            ServiceContext("task", "conversation", "7", "9", 1, 301),
            "token", lambda: None,
        )

        self.assertEqual(result.answer, "元数据结果")
        self.assertEqual(
            runner.java.events[-1][1],
            {"tool": "picture_group_similarity", "available": False},
        )


if __name__ == "__main__":
    unittest.main()
