import unittest
import httpx
from app.runtime.http_client import CircuitBreaker, GuardedTransport


class HttpResilienceTests(unittest.TestCase):
    def test_only_connect_failure_retries_once(self):
        for error,expected in ((httpx.ConnectError,2),(httpx.ReadTimeout,1),(httpx.WriteError,1)):
            calls=[];delays=[]
            def handler(request):
                calls.append(request)
                raise error('hidden endpoint error')
            client=httpx.Client(transport=GuardedTransport(httpx.MockTransport(handler),CircuitBreaker(),delays.append))
            with self.assertRaises(error):
                client.post('https://provider.example/chat/completions',json={'model':'test'})
            self.assertEqual(len(calls),expected)
            self.assertEqual(len(delays),expected-1)

    def test_server_failure_opens_and_single_probe_recovers(self):
        now=[0.];circuit=CircuitBreaker(threshold=2,cooldown=30,clock=lambda:now[0])
        status=[503];calls=[]
        def handler(request):
            calls.append(request)
            return httpx.Response(status[0],stream=httpx.ByteStream(b'safe'))
        client=httpx.Client(transport=GuardedTransport(httpx.MockTransport(handler),circuit,lambda _:None))
        for _ in range(2):
            self.assertEqual(client.get('https://provider.example').status_code,503)
        with self.assertRaises(httpx.ConnectError):
            client.get('https://provider.example')
        self.assertEqual(len(calls),2)
        now[0]=31;status[0]=200
        self.assertEqual(client.get('https://provider.example').status_code,200)
        self.assertEqual(client.get('https://provider.example').status_code,200)

    def test_circuit_origin_registry_is_bounded(self):
        circuit=CircuitBreaker()
        for i in range(100):
            circuit.result(('https',str(i),443),True)
        self.assertEqual(len(circuit.states),32)
