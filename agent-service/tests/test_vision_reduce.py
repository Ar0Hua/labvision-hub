import unittest
import json
import httpx
from app.analysis.vision import VisionAnalyzer
from test_task_runtime import settings


class ReduceTests(unittest.TestCase):
    def test_summary_uses_only_text_and_rejects_unknown_citations(self):
        configured = settings()
        object.__setattr__(configured, "dashscope_api_key", "test")
        object.__setattr__(configured, "vision_model", "vision")
        requests = []
        answer = ["差异 pictureId=999"]
        def handler(request):
            requests.append(json.loads(request.content))
            return httpx.Response(200, json={"choices":[{"message":{"content":answer[0]}}]})
        with httpx.Client(base_url="https://example.com", transport=httpx.MockTransport(handler)) as client:
            analyzer = VisionAnalyzer(configured, client)
            self.assertIsNone(analyzer.summarize("对比", ["观察一", "观察二"], ["1", "2"]))
            answer[0] = "共性 pictureId=1"
            self.assertEqual(analyzer.summarize("对比", ["观察一", "观察二"], ["1", "2"]), answer[0])
        self.assertNotIn("image_url", json.dumps(requests))
        self.assertIn("allowedPictureIds", requests[0]["messages"][1]["content"])
