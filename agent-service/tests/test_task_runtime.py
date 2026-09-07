import base64
import hashlib
import hmac
import json
import time
import unittest

import httpx
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.runtime.java_client import JavaTaskClient, TaskContext
from app.runtime.registry import TaskRegistry
from app.runtime.runner import ExecutorUnavailable, TaskRunner


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
        qdrant_url="http://qdrant",
        qdrant_collection="pictures",
    )


class RecordingRunner:
    def __init__(self) -> None:
        self.calls = []

    def run(self, context, token) -> None:
        self.calls.append((context, token))


class SuccessfulExecutor:
    def execute(self, context: TaskContext) -> str:
        return "找到实验图像"


class MissingExecutor:
    def execute(self, context: TaskContext) -> str:
        raise ExecutorUnavailable()


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
                        "spaceId": "9", "query": "找实验图"}
            else:
                data = True
            return httpx.Response(200, json={"code": 0, "data": data, "message": ""})

        client = httpx.Client(base_url="http://java/api", transport=httpx.MockTransport(handler))
        java = JavaTaskClient(settings(), client)
        signed = self._context()
        TaskRunner(java, SuccessfulExecutor()).run(signed, "token")

        bodies = [json.loads(request.content) for request in requests if request.content]
        self.assertEqual(bodies[0]["status"], "RUNNING")
        self.assertEqual(bodies[1]["eventType"], "answer_delta")
        self.assertEqual(bodies[2]["status"], "SUCCEEDED")
        self.assertTrue(all(request.headers["authorization"] == "Bearer token" for request in requests))

    def test_unavailable_executor_fails_without_placeholder_answer(self):
        bodies = []

        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "GET":
                data = {"taskId": TASK_ID, "conversationId": "conversation", "userId": "7",
                        "spaceId": "9", "query": "找实验图"}
            else:
                bodies.append(json.loads(request.content))
                data = True
            return httpx.Response(200, json={"code": 0, "data": data})

        client = httpx.Client(base_url="http://java/api", transport=httpx.MockTransport(handler))
        TaskRunner(JavaTaskClient(settings(), client), MissingExecutor()).run(self._context(), "token")
        self.assertEqual([body["status"] for body in bodies], ["RUNNING", "FAILED"])
        self.assertEqual(bodies[-1]["errorCode"], "EXECUTOR_UNAVAILABLE")

    def _context(self):
        from app.security.service_token import ServiceContext
        return ServiceContext(TASK_ID, "conversation", "7", "9", 1, 301)


if __name__ == "__main__":
    unittest.main()
