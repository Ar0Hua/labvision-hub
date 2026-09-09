import unittest
from app.runtime.runner import TaskRunner
from app.runtime.java_client import TaskContext, VisionInput
from app.retrieval.keyword_executor import ExecutionResult
from app.security.service_token import ServiceContext


class VisionBatchTests(unittest.TestCase):
    def test_twenty_pictures_batched_and_failed_batch_disclosed(self):
        class Java:
            def __init__(self):
                self.batches = []
            def append_event(self, *_):
                pass
            def get_vision_inputs(self, task, token, ids):
                self.batches.append(ids)
                if len(self.batches) == 2:
                    raise RuntimeError("temporary unavailable")
                return [VisionInput(pictureId=i, spaceId=None,
                    temporaryUrl="https://example.com/" + i, expiresInSeconds=60) for i in ids]
        class Vision:
            enabled = True
            max_pictures = 4
            def analyze(self, query, inputs):
                return "观察：" + ",".join(i.pictureId for i in inputs)
        ids = [str(i) for i in range(1, 21)]
        java = Java()
        runner = TaskRunner(java, object(), Vision())
        context = TaskContext(taskId="t", conversationId="c", userId="1", spaceId=None,
            query="对比", examplePictureIds=ids, status="RUNNING")
        result = runner._add_visual_analysis(
            ExecutionResult("事实", [{"pictureId": i} for i in ids], 20), context,
            ServiceContext("t", "c", "1", None, 1, 301), "token", lambda: None)
        self.assertEqual(len(java.batches), 5)
        self.assertEqual([i for batch in java.batches for i in batch], ids)
        self.assertIn("覆盖 16/20 张", result.answer)
        self.assertIn("批次 5", result.answer)
