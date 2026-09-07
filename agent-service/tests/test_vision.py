import json
import unittest

import httpx
from pydantic import ValidationError

from app.analysis.vision import VisionAnalyzer
from app.runtime.java_client import VisionInput
from test_task_runtime import settings


class VisionAnalyzerTests(unittest.TestCase):
    def test_sends_only_bounded_authorized_inputs_and_returns_observation(self):
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured.update(json.loads(request.content))
            return httpx.Response(200, json={
                "choices": [{"message": {"content": "图片 1 可见曲线图。[pictureId=1]"}}]
            })

        configured = settings()
        object.__setattr__(configured, "dashscope_api_key", "test-key-not-a-real-secret")
        object.__setattr__(configured, "vision_model", "qwen3-vl-plus")
        object.__setattr__(configured, "max_vision_pictures", 1)
        client = httpx.Client(base_url="https://dashscope.example/v1",
                              transport=httpx.MockTransport(handler))
        analyzer = VisionAnalyzer(configured, client)

        answer = analyzer.analyze("比较曲线", [self._input("1"), self._input("2")])

        self.assertIn("pictureId=1", answer)
        user_content = captured["messages"][0]["content"]
        self.assertEqual(len([item for item in user_content if item["type"] == "image_url"]), 1)
        self.assertNotIn("https://signed.example/2", str(user_content))

    def test_model_failure_degrades_to_no_visual_observation(self):
        configured = settings()
        object.__setattr__(configured, "dashscope_api_key", "test-key-not-a-real-secret")
        object.__setattr__(configured, "vision_model", "qwen3-vl-plus")
        client = httpx.Client(base_url="https://dashscope.example/v1",
                              transport=httpx.MockTransport(lambda _: httpx.Response(503)))
        self.assertIsNone(VisionAnalyzer(configured, client).analyze("分析", [self._input("1")]))

    def test_rejects_non_https_or_credentialed_image_url(self):
        with self.assertRaises(ValidationError):
            self._input("1", "http://signed.example/1")
        with self.assertRaises(ValidationError):
            self._input("1", "https://user:pass@signed.example/1")

    @staticmethod
    def _input(picture_id: str, url: str | None = None) -> VisionInput:
        return VisionInput(
            pictureId=picture_id, spaceId="9", name="曲线图", introduction=None,
            category="实验结果", tags="[]", width=256, height=256, size=1024, format="png",
            temporaryUrl=url or f"https://signed.example/{picture_id}?token=short",
            expiresInSeconds=120,
        )


if __name__ == "__main__":
    unittest.main()
