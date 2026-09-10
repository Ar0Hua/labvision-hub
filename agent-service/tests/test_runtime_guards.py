import unittest
import json
import httpx
from app.config import validate_model_endpoints
from app.retrieval.intent import IntentParser
from app.graph.workflow import LangGraphWorkflow
from test_semantic import settings

class RuntimeGuardTests(unittest.TestCase):
    def test_provider_allowlist_rejects_credentials_insecure_and_suffix_hosts(self):
        allowed={'dashscope.aliyuncs.com'}
        validate_model_endpoints(['https://dashscope.aliyuncs.com/api/v1'],allowed)
        for url in ('http://dashscope.aliyuncs.com','https://dashscope.aliyuncs.com.evil.example',
                    'https://user:pass@dashscope.aliyuncs.com','https://127.0.0.1',
                    'https://dashscope.aliyuncs.com:8443','https://dashscope.aliyuncs.com/?token=x'):
            with self.assertRaises(RuntimeError):
                validate_model_endpoints([url],allowed)

    def test_one_schema_repair_then_deterministic_fallback(self):
        requests=[]
        def handler(request):
            requests.append(json.loads(request.content))
            return httpx.Response(200,json={'choices':[{'message':{'content':'NOT_JSON_SECRET'}}]})
        parser=IntentParser(settings(),httpx.Client(base_url='https://model.example',transport=httpx.MockTransport(handler)))
        result=parser.parse('显微镜')
        self.assertEqual(result.searchText,'显微镜')
        self.assertEqual(len(requests),2)
        self.assertNotIn('NOT_JSON_SECRET',json.dumps(requests[1]))

    def test_graph_has_explicit_recursion_ceiling(self):
        from types import SimpleNamespace
        self.assertEqual(LangGraphWorkflow(None,None,6)._config(
            SimpleNamespace(userId='u',conversationId='c'))['recursion_limit'],6)
