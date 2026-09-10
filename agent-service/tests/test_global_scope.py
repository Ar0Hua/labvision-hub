import unittest
from types import SimpleNamespace
from app.retrieval.semantic import SemanticRetriever
from app.retrieval.keyword_executor import KeywordSearchExecutor
from app.retrieval.intent import SearchIntent
from app.runtime.java_client import TaskContext


class GlobalScopeTests(unittest.TestCase):
    def test_public_review_is_nested_not_applied_to_private_branches(self):
        result=SemanticRetriever._filter(["public","space:9"],{"brightness":"dark"})
        self.assertEqual(len(result["should"]),2)
        public,private=result["should"]
        self.assertIn({"key":"reviewStatus","match":{"value":1}},public["must"])
        self.assertNotIn({"key":"reviewStatus","match":{"value":1}},private["must"])
        for branch in result["should"]:
            self.assertIn({"key":"isDelete","match":{"value":0}},branch["must"])
            self.assertIn({"key":"brightnessScore","range":{"lt":50}},branch["must"])
        for invalid in ([],["public","public"],["space:0"],["anything"]):
            with self.assertRaises(ValueError): SemanticRetriever._filter(invalid)

    def test_executor_uses_only_java_context_snapshot_not_model_scope(self):
        calls=[]
        semantic=SimpleNamespace(enabled=True,search=lambda *args:calls.append(args[1]) or [])
        parser=SimpleNamespace(parse=lambda *_:SearchIntent(searchText="图"))
        context=TaskContext(taskId="t",conversationId="c",userId="1",spaceId=None,
                            allSpaces=True,allowedSpaceIds=["9","10"],query="搜索",status="RUNNING")
        KeywordSearchExecutor(parser,semantic).execute(context,lambda *_:[],lambda _:[],lambda:None)
        self.assertEqual(calls,[["public","space:9","space:10"]])
