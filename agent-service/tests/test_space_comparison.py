import json
import unittest
from app.runtime.runner import TaskRunner
from app.runtime.java_client import TaskContext
from app.security.service_token import ServiceContext
from test_space_statistics import summary


class ComparisonTests(unittest.TestCase):
    def test_comparison_routes_to_java_and_skips_search(self):
        class Java:
            def __init__(self):
                self.states = []
                self.events = []
            def get_context(self, *_):
                return TaskContext(taskId="t", conversationId="c", userId="1", spaceId=None,
                    query="比较空间9、10的图片数量", status="RUNNING" if self.states else "PENDING")
            def get_space_comparison(self, *_):
                first = summary()
                second = summary()
                second.scope.spaceId = "10"
                return [first, second]
            def update_state(self, *_, **value):
                self.states.append(value)
            def append_event(self, task, token, kind, payload):
                self.events.append((kind, json.loads(payload)))
            def close(self):
                pass
        class Executor:
            def execute(self, *_):
                raise AssertionError("comparison must not search")
        java = Java()
        TaskRunner(java, Executor()).run(ServiceContext("t", "c", "1", None, 1, 301), "token")
        self.assertEqual(java.states[-1]["status"], "SUCCEEDED")
        answer = next(value["text"] for kind, value in java.events if kind == "answer_delta")
        self.assertIn("| 9 | 12 |", answer)
        self.assertIn("| 10 | 12 |", answer)
