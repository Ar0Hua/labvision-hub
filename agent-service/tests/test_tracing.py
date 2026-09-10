import json
import unittest
import httpx
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from app.observability.tracing import provider, span, trace_headers, safe_parent
from app.runtime.java_client import JavaTaskClient
from app.observability.metrics import RuntimeMetrics
from test_task_runtime import settings


class TracingTests(unittest.TestCase):
    def test_real_sdk_parent_propagation_and_redaction(self):
        exporter=InMemorySpanExporter()
        provider.add_span_processor(SimpleSpanProcessor(exporter))
        parent='00-'+'1'*32+'-'+'2'*16+'-01'
        requests=[]
        def handler(request):
            requests.append(request)
            return httpx.Response(200,json={'code':0,'data':None})
        java=JavaTaskClient(settings(),httpx.Client(base_url='http://java',transport=httpx.MockTransport(handler)))
        with self.assertLogs('labvision.trace',level='INFO') as logs:
            with span('agent.task',parent):
                java.append_event('t','SECRET_BEARER','answer_delta','SECRET_IMAGE_BYTES')
                self.assertEqual(trace_headers()['traceparent'][3:35],'1'*32)
            with self.assertRaises(ValueError):
                with span('model.vision_stream',parent):
                    raise ValueError('SECRET_PROMPT https://signed.example/?token=SECRET')
        spans=exporter.get_finished_spans()
        self.assertTrue(all(s.context.trace_id==int('1'*32,16) for s in spans))
        self.assertEqual(requests[0].headers['traceparent'][3:35],'1'*32)
        self.assertFalse(any(s.events for s in spans))
        output=''.join(logs.output)+str([dict(s.attributes) for s in spans])
        self.assertNotIn('SECRET',output)
        self.assertEqual(spans[-1].status.status_code.name,'ERROR')

    def test_invalid_parent_and_bounded_metric_labels(self):
        self.assertIsNone(safe_parent('00-'+'0'*32+'-'+'2'*16+'-01'))
        self.assertIsNone(safe_parent('header\ninjection'))
        metrics=RuntimeMetrics();metrics.observe_operation('secret-user-123',2,True)
        output=metrics.render()
        self.assertNotIn('secret-user',output)
        self.assertIn('operation="other",le="3"} 1',output)
        self.assertIn('operation_errors_total{operation="other"} 1',output)
