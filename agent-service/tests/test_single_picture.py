import json
import unittest
from app.runtime.runner import TaskRunner
from app.runtime.java_client import TaskContext, PictureCandidate
from app.security.service_token import ServiceContext


class SinglePictureTests(unittest.TestCase):
    def test_selected_picture_is_analyzed_without_search(self):
        class Java:
            def __init__(self):
                self.events = []
                self.states = []
            def get_context(self, *_):
                return TaskContext(taskId="t", conversationId="c", userId="1", spaceId=None,
                    query="分析这张图", examplePictureIds=["2"],
                    status="RUNNING" if self.states else "PENDING")
            def authorize_pictures(self, task, token, ids):
                self.ids = ids
                return [PictureCandidate(pictureId="2", spaceId=None, name="样本")]
            def update_state(self, *_, **state):
                self.states.append(state)
            def append_event(self, task, token, kind, payload):
                self.events.append((kind, json.loads(payload)))
            def close(self):
                pass
        class Executor:
            def execute(self, *_):
                raise AssertionError("single analysis must not search")
        java = Java()
        TaskRunner(java, Executor()).run(ServiceContext("t", "c", "1", None, 1, 301), "token")
        self.assertEqual(java.ids, ["2"])
        self.assertEqual(java.states[-1]["status"], "SUCCEEDED")
        answer = next(value["text"] for kind, value in java.events if kind == "answer_delta")
        self.assertIn("选中图片：[图片 ID: 2]", answer)
