import base64
import hashlib
import hmac
import json
import time
import unittest
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.runtime.java_client import JavaTaskClient, TaskContext
from app.runtime.registry import TaskRegistry
from app.runtime.runner import ExecutorUnavailable, TaskRunner
from app.retrieval.keyword_executor import ExecutionResult


SECRET = "0123456789abcdef0123456789abcdef"
TASK_ID = "11111111-1111-1111-1111-111111111111"


def issue(now: int) -> str:
    payload = {
        "taskId": TASK_ID,
        "conversationId": "conversation",
        "userId": "7",
        "spaceId": "9",
        "issuedAt": now,
        "expiresAt": now + 300,
    }
    body = base64.urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":")).encode()
    ).rstrip(b"=").decode()
    signature = hmac.new(SECRET.encode(), body.encode(), hashlib.sha256).digest()
    return body + "." + base64.urlsafe_b64encode(signature).rstrip(b"=").decode()


def settings() -> Settings:
    return Settings(
        java_base_url="http://java/api",
        service_secret=SECRET,
        java_timeout_seconds=10,
        dashscope_api_key="",
        dashscope_base_url="https://dashscope.example/v1",
        chat_model="qwen-plus",
        model_timeout_seconds=20,
        embedding_model="text-embedding-v4",
        embedding_dimensions=1024,
        qdrant_url="http://qdrant",
        qdrant_api_key="",
        qdrant_collection="pictures",
        qdrant_timeout_seconds=5,
    )


class RecordingRunner:
    def __init__(self) -> None:
        self.calls = []

    def run(self, context, token) -> None:
        self.calls.append((context, token))


class SuccessfulExecutor:
    def execute(self, context: TaskContext, search, authorize, check_active) -> ExecutionResult:
        return ExecutionResult("找到实验图像", [{"pictureId": "1", "name": "图像", "category": None}], 1)


class MissingExecutor:
    def execute(self, context: TaskContext, search, authorize, check_active) -> ExecutionResult:
        raise ExecutorUnavailable()


class SuccessfulVision:
    enabled = True
    max_pictures = 8

    def analyze(self, query, pictures):
        return f"已分析 {len(pictures)} 张图片，目标：{query}"


class TaskRuntimeTests(unittest.TestCase):
    def test_endpoint_verifies_token_and_deduplicates_replay(self):
        now = int(time.time())
        token = issue(now)
        runner = RecordingRunner()
        app = create_app(lambda: settings(), lambda _: runner, TaskRegistry())
        client = TestClient(app)
        headers = {"Authorization": f"Bearer {token}"}

        first = client.post(f"/internal/tasks/{TASK_ID}/run", headers=headers)
        second = client.post(f"/internal/tasks/{TASK_ID}/run", headers=headers)

        self.assertEqual(first.status_code, 202)
        self.assertTrue(first.json()["accepted"])
        self.assertFalse(second.json()["accepted"])
        self.assertEqual(len(runner.calls), 1)
        self.assertEqual(
            client.post(f"/internal/tasks/{TASK_ID}/run", headers={"Authorization": "Bearer bad"}).status_code,
            401,
        )

    def test_runner_writes_answer_and_terminal_state(self):
        requests = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            if request.method == "GET":
                data = {"taskId": TASK_ID, "conversationId": "conversation", "userId": "7",
                        "spaceId": "9", "query": "找实验图", "status": "PENDING" if len(requests) == 1 else "RUNNING"}
            else:
                data = True
            return httpx.Response(200, json={"code": 0, "data": data, "message": ""})

        client = httpx.Client(base_url="http://java/api", transport=httpx.MockTransport(handler))
        java = JavaTaskClient(settings(), client)
        signed = self._context()
        TaskRunner(java, SuccessfulExecutor()).run(signed, "token")

        bodies = [json.loads(request.content) for request in requests if request.content]
        self.assertEqual(bodies[0]["status"], "RUNNING")
        self.assertEqual(bodies[1]["eventType"], "tool_start")
        self.assertEqual(bodies[2]["eventType"], "tool_result")
        self.assertEqual(bodies[3]["eventType"], "citation")
        self.assertEqual(bodies[4]["eventType"], "answer_delta")
        self.assertEqual(bodies[5]["status"], "SUCCEEDED")
        self.assertTrue(all(request.headers["authorization"] == "Bearer token" for request in requests))

    def test_unavailable_executor_fails_without_placeholder_answer(self):
        bodies = []

        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "GET":
                data = {"taskId": TASK_ID, "conversationId": "conversation", "userId": "7",
                        "spaceId": "9", "query": "找实验图", "status": "PENDING" if not bodies else "RUNNING"}
            else:
                bodies.append(json.loads(request.content))
                data = True
            return httpx.Response(200, json={"code": 0, "data": data})

        client = httpx.Client(base_url="http://java/api", transport=httpx.MockTransport(handler))
        TaskRunner(JavaTaskClient(settings(), client), MissingExecutor()).run(self._context(), "token")
        states = [body for body in bodies if "status" in body]
        self.assertEqual([body["status"] for body in states], ["RUNNING", "FAILED"])
        self.assertEqual(states[-1]["errorCode"], "EXECUTOR_UNAVAILABLE")

    def test_cancelled_task_does_not_emit_answer_or_failed_state(self):
        bodies = []
        get_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal get_count
            if request.method == "GET":
                get_count += 1
                data = {"taskId": TASK_ID, "conversationId": "conversation", "userId": "7",
                        "spaceId": "9", "query": "找实验图",
                        "status": "PENDING" if get_count == 1 else "CANCELLED"}
            else:
                bodies.append(json.loads(request.content)); data = True
            return httpx.Response(200, json={"code": 0, "data": data})

        client = httpx.Client(base_url="http://java/api", transport=httpx.MockTransport(handler))
        TaskRunner(JavaTaskClient(settings(), client), SuccessfulExecutor()).run(self._context(), "token")
        event_types = [body.get("eventType") for body in bodies]
        states = [body["status"] for body in bodies if "status" in body]
        self.assertNotIn("answer_delta", event_types)
        self.assertEqual(states, ["RUNNING"])

    def test_runner_fetches_authorized_vision_inputs_before_model_analysis(self):
        requests = []
        get_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal get_count
            requests.append(request)
            if request.method == "GET":
                get_count += 1
                data = {"taskId": TASK_ID, "conversationId": "conversation", "userId": "7",
                        "spaceId": "9", "query": "分析实验图",
                        "status": "PENDING" if get_count == 1 else "RUNNING"}
            elif request.url.path.endswith("/pictures/vision-inputs"):
                data = [{"pictureId": "1", "spaceId": "9", "name": "图像",
                         "introduction": None, "category": None, "tags": "[]", "width": 256,
                         "height": 256, "size": 1024, "format": "png",
                         "temporaryUrl": "https://signed.example/1?token=short",
                         "expiresInSeconds": 120}]
            else:
                data = True
            return httpx.Response(200, json={"code": 0, "data": data})

        client = httpx.Client(base_url="http://java/api", transport=httpx.MockTransport(handler))
        runner = TaskRunner(JavaTaskClient(settings(), client), SuccessfulExecutor(), SuccessfulVision())
        runner.run(self._context(), "token")

        self.assertTrue(any(request.url.path.endswith("/pictures/vision-inputs") for request in requests))
        event_bodies = [json.loads(request.content) for request in requests if request.content]
        answers = [body for body in event_bodies if body.get("eventType") == "answer_delta"]
        self.assertIn("视觉模型观察", "".join(json.loads(body["payloadJson"])["text"] for body in answers))
        tools = [json.loads(body["payloadJson"])["tool"] for body in event_bodies
                 if body.get("eventType") == "tool_result"]
        self.assertEqual(tools, ["picture_keyword_search", "vision_analysis"])

    def test_total_deadline_has_distinct_failure_code(self):
        bodies = []
        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "GET":
                data = {"taskId": TASK_ID, "conversationId": "conversation", "userId": "7",
                        "spaceId": "9", "query": "找实验图", "status": "PENDING"}
            else:
                bodies.append(json.loads(request.content)); data = True
            return httpx.Response(200, json={"code": 0, "data": data})

        client = httpx.Client(base_url="http://java/api", transport=httpx.MockTransport(handler))
        with patch("app.runtime.runner.time.monotonic", side_effect=[0, 11, 11]):
            TaskRunner(JavaTaskClient(settings(), client), SuccessfulExecutor(), timeout_seconds=10).run(
                self._context(), "token")
        states = [body for body in bodies if "status" in body]
        self.assertEqual(states[-1]["status"], "FAILED")
        self.assertEqual(states[-1]["errorCode"], "TASK_TIMEOUT")

    def _context(self):
        from app.security.service_token import ServiceContext
        return ServiceContext(TASK_ID, "conversation", "7", "9", 1, 301)


if __name__ == "__main__":
    unittest.main()
