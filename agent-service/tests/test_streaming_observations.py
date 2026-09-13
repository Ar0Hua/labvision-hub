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
    def test_unanchored_paragraphs_are_skipped_without_losing_verified_answer(self):
        emitted = []
        class Response:
            def iter_lines(self):
                yield event('观察摘要\n\n').strip()
                yield event('pictureId=1 可见河道\n\n').strip()
                assert emitted == ['pictureId=1 可见河道\n\n']
                yield event('综上，其他内容无法确认。\n\n').strip()
                yield 'data: [DONE]'
        result = read_observations(Response(), 'model', ['1'], emitted.append, lambda: None)
        self.assertEqual(result, 'pictureId=1 可见河道\n\n')
        self.assertNotIn('观察摘要', ''.join(emitted))
        self.assertNotIn('综上', ''.join(emitted))
        self.assertIn('2 段', emitted[-1])

    def test_only_unanchored_text_is_not_a_successful_analysis(self):
        class Response:
            def iter_lines(self):
                return iter([event('没有任何可核验图片引用').strip(), 'data: [DONE]'])
        emitted = []
        with self.assertRaisesRegex(ValueError, 'no verified visual observations'):
            read_observations(Response(), 'model', ['1'], emitted.append, lambda: None)
        self.assertEqual(emitted, [])

    def test_unanchored_urls_and_unknown_ids_still_fail_closed(self):
        for invalid in ['https://private.example/image', 'pictureId=999 非法图片']:
            class Response:
                def iter_lines(self):
                    return iter([event('pictureId=1 合法\n\n').strip(), event(invalid).strip(), 'data: [DONE]'])
            emitted = []
            with self.assertRaises(ValueError):
                read_observations(Response(), 'model', ['1'], emitted.append, lambda: None)
            self.assertEqual(emitted, ['pictureId=1 合法\n\n'])

    def test_temporary_image_observation_does_not_require_picture_id(self):
        class Response:
            def iter_lines(self):
                return iter([event('临时图片可见河道').strip(), 'data: [DONE]'])
        emitted = []
        self.assertEqual(read_observations(Response(), 'model', [], emitted.append, lambda: None), '临时图片可见河道')

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
