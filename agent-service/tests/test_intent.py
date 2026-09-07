import json
import unittest

import httpx

from app.config import Settings
from app.retrieval.intent import IntentParser


def settings(api_key: str = "key") -> Settings:
    return Settings("http://java", "x" * 32, 10, api_key, "https://dashscope.example/v1",
                    "qwen-plus", 20, "http://qdrant", "pictures")


class IntentParserTests(unittest.TestCase):
    def test_dashscope_json_is_strictly_validated(self):
        seen = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen.append(json.loads(request.content))
            content = json.dumps({"searchText": "细胞", "category": "显微成像",
                                  "tags": ["荧光染色"], "limit": 8}, ensure_ascii=False)
            return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})

        client = httpx.Client(base_url="https://dashscope.example/v1",
                              transport=httpx.MockTransport(handler))
        intent = IntentParser(settings(), client).parse("查找细胞荧光图")
        self.assertEqual(intent.category, "显微成像")
        self.assertEqual(intent.tags, ["荧光染色"])
        self.assertEqual(seen[0]["response_format"], {"type": "json_object"})

    def test_invalid_model_output_and_missing_key_fall_back(self):
        bad = httpx.Client(base_url="https://dashscope.example/v1", transport=httpx.MockTransport(
            lambda _request: httpx.Response(200, json={"choices": [{"message": {"content": "not json"}}]})
        ))
        self.assertEqual(IntentParser(settings(), bad).parse("  实验   仪器  ").searchText, "实验 仪器")
        self.assertEqual(IntentParser(settings("")).parse("显微图").searchText, "显微图")


if __name__ == "__main__":
    unittest.main()
