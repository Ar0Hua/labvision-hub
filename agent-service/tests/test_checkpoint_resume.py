import unittest
from langgraph.checkpoint.memory import InMemorySaver
from app.graph.workflow import LangGraphWorkflow
from app.retrieval.keyword_executor import ExecutionResult
from app.runtime.java_client import TaskContext


class ResumeTests(unittest.TestCase):
    def test_completed_retrieval_is_reauthorized_before_resuming_answer(self):
        from types import SimpleNamespace
        executor=SimpleNamespace(execute=lambda *_:ExecutionResult('OLD_PRIVATE_METADATA',[{'pictureId':'1'}],1))
        workflow=LangGraphWorkflow(executor,InMemorySaver())
        context=TaskContext(taskId='t',conversationId='c',userId='1',spaceId=None,query='q',status='RUNNING')
        checks=[0]
        def interrupt():
            checks[0]+=1
            if checks[0]==3:
                raise RuntimeError('interrupt before final checkpoint')
        with self.assertRaises(RuntimeError):
            workflow.execute(context,lambda *_:[],lambda *_:[],interrupt)
        with self.assertRaisesRegex(ValueError,'no longer authorized'):
            workflow.execute(context,lambda *_:[],lambda *_:[],lambda:None)

    def test_retries_interrupted_node_without_repeating_prepare(self):
        class Executor:
            calls = 0
            def execute(self, *_):
                self.calls += 1
                if self.calls == 1:
                    raise RuntimeError("interrupted")
                return ExecutionResult("done", [], 0)
        checks = []
        executor = Executor()
        workflow = LangGraphWorkflow(executor, InMemorySaver())
        context = TaskContext(taskId="t", conversationId="c", userId="1", spaceId=None,
            query="q", status="RUNNING")
        args = (context, lambda *_: [], lambda *_: [], lambda: checks.append(1))
        with self.assertRaises(RuntimeError):
            workflow.execute(*args)
        self.assertEqual(workflow.execute(*args).answer, "done")
        self.assertEqual(len(checks), 4)
