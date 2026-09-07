import unittest

from app.graph.workflow import LangGraphWorkflow
from app.retrieval.keyword_executor import ExecutionResult
from app.runtime.java_client import TaskContext


class QueryExecutor:
    def execute(self, context, search, authorize, check_active):
        check_active()
        return ExecutionResult(
            answer="结果：" + context.query,
            citations=[{"pictureId": context.taskId, "name": context.query, "category": None}],
            candidate_count=1,
        )


class WorkflowTests(unittest.TestCase):
    def test_checkpoint_keeps_bounded_structured_memory_between_turns(self):
        from langgraph.checkpoint.memory import InMemorySaver

        workflow = LangGraphWorkflow(QueryExecutor(), InMemorySaver())
        first = self._context("task-1", "第一轮")
        second = self._context("task-2", "第二轮")

        self.assertEqual(workflow.execute(first, lambda *_: [], lambda _: [], lambda: None).answer,
                         "结果：第一轮")
        self.assertEqual(workflow.execute(second, lambda *_: [], lambda _: [], lambda: None).answer,
                         "结果：第二轮")

        state = workflow.state(second)
        self.assertEqual([turn["query"] for turn in state["recent_turns"]], ["第一轮", "第二轮"])
        self.assertEqual(state["recent_turns"][1]["pictureIds"], ["task-2"])

    def test_different_users_do_not_share_same_conversation_checkpoint(self):
        from langgraph.checkpoint.memory import InMemorySaver

        workflow = LangGraphWorkflow(QueryExecutor(), InMemorySaver())
        first = self._context("task-1", "用户一")
        other = self._context("task-2", "用户二", user_id="8")
        workflow.execute(first, lambda *_: [], lambda _: [], lambda: None)
        workflow.execute(other, lambda *_: [], lambda _: [], lambda: None)

        self.assertEqual([turn["query"] for turn in workflow.state(other)["recent_turns"]], ["用户二"])

    @staticmethod
    def _context(task_id: str, query: str, user_id: str = "7") -> TaskContext:
        return TaskContext(
            taskId=task_id,
            conversationId="conversation",
            userId=user_id,
            spaceId="9",
            query=query,
            status="RUNNING",
        )


if __name__ == "__main__":
    unittest.main()
