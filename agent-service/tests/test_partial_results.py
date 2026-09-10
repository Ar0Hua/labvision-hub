import json
import unittest
from types import SimpleNamespace

from app.runtime.runner import TaskRunner, TaskDeadlineExceeded
from app.runtime.budget import BudgetExceeded
from app.runtime.java_client import TaskContext
from app.retrieval.keyword_executor import ExecutionResult
from app.security.service_token import ServiceContext


class RecordingJava:
    def __init__(self):
        self.events=[]
        self.states=[]
    def get_context(self,*_):
        return TaskContext(taskId="t",conversationId="c",userId="1",spaceId=None,query="搜索图",
                           status="RUNNING" if self.states else "PENDING")
    def update_state(self,*_,**state):
        self.states.append(state)
    def append_event(self,task,token,kind,payload):
        self.events.append((kind,json.loads(payload)))
    def close(self):
        pass


class PartialResultsTests(unittest.TestCase):
    def test_timeout_budget_and_error_keep_base_answer(self):
        for exception, code in ((TaskDeadlineExceeded,"TASK_TIMEOUT"),(BudgetExceeded,"BUDGET_EXCEEDED"),(RuntimeError,"AGENT_INTERNAL_ERROR")):
            java=RecordingJava()
            class FailingRunner(TaskRunner):
                def _add_visual_analysis(self,*_):
                    assert any(kind=="answer_delta" for kind,_ in self.java.events)
                    raise exception()
            executor=SimpleNamespace(execute=lambda *_: ExecutionResult("已完成的检索结果",[{"pictureId":"1"}],1))
            FailingRunner(java,executor).run(ServiceContext("t","c","1",None,1,301),"token")
            self.assertEqual(java.states[-1]["error_code"],code)
            self.assertIn("已保留",java.states[-1]["error_message"])
            self.assertIn("VISUAL_ANALYSIS",java.states[-1]["error_message"])
            self.assertEqual("".join(value["text"] for kind,value in java.events if kind=="answer_delta"),"已完成的检索结果")

    def test_append_only_deltas_do_not_repeat_and_are_bounded(self):
        java=RecordingJava()
        base="元数据"*1500
        class EnrichingRunner(TaskRunner):
            def _add_visual_analysis(self,result,*_):
                return ExecutionResult(result.answer+"\n视觉补充",[],0)
        executor=SimpleNamespace(execute=lambda *_:ExecutionResult(base,[],0))
        EnrichingRunner(java,executor).run(ServiceContext("t","c","1",None,1,301),"token")
        deltas=[value["text"] for kind,value in java.events if kind=="answer_delta"]
        self.assertTrue(all(len(value)<=2048 for value in deltas))
        self.assertEqual("".join(deltas),base+"\n视觉补充")
        self.assertEqual(java.states[-1]["status"],"SUCCEEDED")
