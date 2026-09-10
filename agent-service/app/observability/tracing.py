"""OpenTelemetry spans with an allowlisted, local JSON exporter; no prompt/body capture."""
from contextlib import contextmanager
from functools import wraps
import json
import logging
import re
from app.observability.metrics import runtime_metrics
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter, SpanExportResult
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

log = logging.getLogger("labvision.trace")
PROPAGATOR = TraceContextTextMapPropagator()


class SafeJsonExporter(SpanExporter):
    def export(self, spans):
        for item in spans:
            runtime_metrics.observe_operation(item.name, (item.end_time-item.start_time)/1e9,
                                              item.status.status_code.name == 'ERROR')
            log.info(json.dumps({"event":"agent_span", "name":item.name,
                "traceId":format(item.context.trace_id,'032x'),
                "spanId":format(item.context.span_id,'016x'),
                "parentSpanId":format(item.parent.span_id,'016x') if item.parent else None,
                "durationMs":round((item.end_time-item.start_time)/1e6,3),
                "status":item.status.status_code.name}, separators=(',',':')))
        return SpanExportResult.SUCCESS


provider = TracerProvider(resource=Resource({"service.name":"labvision-agent"}))
provider.add_span_processor(SimpleSpanProcessor(SafeJsonExporter()))
tracer = provider.get_tracer("labvision.agent", "p0-v1")


def safe_parent(value):
    if not isinstance(value,str) or not re.fullmatch(r"00-[0-9a-f]{32}-[0-9a-f]{16}-0[01]", value):
        return None
    if value[3:35] == '0'*32 or value[36:52] == '0'*16:
        return None
    return value


@contextmanager
def span(name, parent=None):
    context = PROPAGATOR.extract({"traceparent":safe_parent(parent)}) if safe_parent(parent) else None
    with tracer.start_as_current_span(name, context=context, record_exception=False,
                                     set_status_on_exception=False) as current:
        try:
            yield current
        except BaseException:
            current.set_status(trace.Status(trace.StatusCode.ERROR))
            raise


def traced(name):
    def decorate(function):
        @wraps(function)
        def wrapped(*args, **kwargs):
            with span(name):
                return function(*args, **kwargs)
        return wrapped
    return decorate


def trace_headers():
    headers = {}
    PROPAGATOR.inject(headers)
    return headers


def set_outcome(outcome):
    trace.get_current_span().set_status(trace.Status(
        trace.StatusCode.ERROR if outcome in {'failed','timeout','budget','unavailable'} else trace.StatusCode.OK))


def run_traced(runner, context, token, parent):
    with span("agent.dispatch", parent):
        runner.run(context, token)


def configure_logging():
    if not log.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(message)s'))
        log.addHandler(handler)
    log.setLevel(logging.INFO)
    log.propagate = False
