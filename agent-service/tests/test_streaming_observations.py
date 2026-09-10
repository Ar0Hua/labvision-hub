import json
import unittest
import httpx
from app.analysis.streaming import read_observations
from app.analysis.vision import VisionAnalyzer
import test_vision
from test_semantic import settings


def event(content):
    return 'data: '+json.dumps({'choices':[{'delta':{'content':content,'reasoning_content':'NEVER PUBLISH'}}]})+'\n\n'

class StreamingObservationTests(unittest.TestCase):
    def test_incremental_paragraph_and_hidden_reasoning(self):
        emitted=[]
        class Response:
            def iter_lines(self):
                yield event('第一段 pictureId=1\n\n').strip()
                assert emitted == ['第一段 pictureId=1\n\n']
                yield event('第二段 picture').strip()
                yield event('Id=1').strip()
                yield 'data: [DONE]'
        answer=read_observations(Response(),'model',['1'],emitted.append,lambda:None)
        self.assertEqual(answer,''.join(emitted))
        self.assertNotIn('NEVER',answer)

    def test_bad_citation_or_disconnect_preserves_verified_prefix(self):
        for ending in ([event('泄露 pictureId=999').strip(),'data: [DONE]'], []):
            emitted=[]
            class Response:
                def iter_lines(self):
                    return iter([event('可见 pictureId=1\n\n').strip(),*ending])
            with self.assertRaises(ValueError):
                read_observations(Response(),'model',['1'],emitted.append,lambda:None)
            self.assertEqual(emitted,['可见 pictureId=1\n\n'])

    def test_adapter_requests_stream_and_usage(self):
        captured=[]
        def handler(request):
            captured.append(json.loads(request.content))
            return httpx.Response(200,headers={'Content-Type':'text/event-stream'},
                text=event('观察 pictureId=1\n\n')+'data: [DONE]\n\n')
        configured=settings(); object.__setattr__(configured,'vision_model','vision')
        client=httpx.Client(base_url='https://model.example',transport=httpx.MockTransport(handler))
        emitted=[]
        VisionAnalyzer(configured,client).analyze_stream('分析',[test_vision.VisionAnalyzerTests._input('1')],emitted.append,lambda:None)
        self.assertTrue(captured[0]['stream'])
        self.assertTrue(captured[0]['stream_options']['include_usage'])
        self.assertEqual(emitted,['观察 pictureId=1\n\n'])
