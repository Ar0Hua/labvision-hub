"""Bounded per-origin circuit breaker; retry only failures before connection establishment."""
from collections import OrderedDict
from threading import Lock
import random
import time
import httpx
from app.runtime.budget import reserve


class CircuitBreaker:
    def __init__(self, threshold=5, cooldown=30, clock=time.monotonic):
        self.threshold, self.cooldown, self.clock = threshold, cooldown, clock
        self.states = OrderedDict()
        self.lock = Lock()

    def before(self, origin):
        with self.lock:
            count, until = self.states.get(origin,(0,0))
            if until > self.clock():
                raise httpx.ConnectError('dependency circuit is open')
            if until:
                # One half-open probe per origin; concurrent probes wait for its result.
                self.states[origin] = (count,self.clock()+self.cooldown)

    def result(self, origin, failed):
        with self.lock:
            count, _ = self.states.get(origin,(0,0))
            count = count+1 if failed else 0
            self.states[origin] = (count,self.clock()+self.cooldown if count>=self.threshold else 0)
            self.states.move_to_end(origin)
            while len(self.states)>32:
                self.states.popitem(last=False)


breaker = CircuitBreaker()


class GuardedStream(httpx.SyncByteStream):
    def __init__(self, stream, circuit, origin, healthy):
        self.stream,self.circuit,self.origin,self.healthy = stream,circuit,origin,healthy
    def __iter__(self):
        try:
            yield from self.stream
        except httpx.TransportError:
            self.circuit.result(self.origin,True)
            raise
        else:
            if self.healthy:
                self.circuit.result(self.origin,False)
    def close(self):
        self.stream.close()


class GuardedTransport(httpx.BaseTransport):
    def __init__(self, transport=None, circuit=breaker, sleep=time.sleep):
        self.transport = transport or httpx.HTTPTransport(retries=0)
        self.circuit,self.sleep = circuit,sleep
    def handle_request(self, request):
        origin = (request.url.scheme,request.url.host,request.url.port)
        self.circuit.before(origin)
        for attempt in range(2):
            try:
                response = self.transport.handle_request(request)
                unhealthy = response.status_code==429 or response.status_code>=500
                if unhealthy:
                    self.circuit.result(origin,True)
                response.stream = GuardedStream(response.stream,self.circuit,origin,not unhealthy)
                return response
            except (httpx.ConnectError,httpx.ConnectTimeout):
                self.circuit.result(origin,True)
                if attempt:
                    raise
                reserve()  # No bytes have reached the provider; no extra billed model generation.
                self.sleep(.1*(2**attempt)+random.uniform(0,.1))
                self.circuit.before(origin)
            except httpx.TransportError:
                self.circuit.result(origin,True)
                raise  # Never replay ambiguous writes, model generations or SSE streams.
    def close(self):
        self.transport.close()


def client(*args, **kwargs):
    if 'transport' not in kwargs:
        kwargs['transport'] = GuardedTransport()
    kwargs.setdefault('follow_redirects',False)
    return httpx.Client(*args,**kwargs)
