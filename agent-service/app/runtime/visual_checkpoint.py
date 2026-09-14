"""Task-local completed visual batches. Always reauthorize and refresh source versions before lookup."""
import hashlib
import hmac
import json


class VisualBatchCheckpoint:
    VERSION = 'visual-batch-v1'

    def __init__(self, settings):
        self.url = settings.checkpoint_redis_url
        self.secret = settings.service_secret.encode()
        self.ttl = settings.checkpoint_ttl_minutes * 60
        self.model = settings.vision_model

    def key(self, context, pictures):
        if not pictures or any(not p.sourceVersion for p in pictures):
            return None  # Older backends cannot establish freshness; never reuse stale observations.
        data = {'version':self.VERSION,'model':self.model,'task':context.taskId,
                'user':context.userId,'conversation':context.conversationId,'query':context.query,
                'pictures':[p.model_dump(exclude={'temporaryUrl','expiresInSeconds'}) for p in pictures]}
        digest = hashlib.sha256(json.dumps(data,sort_keys=True,ensure_ascii=False,default=str).encode()).hexdigest()
        return 'labvision:visual-batch:'+digest

    def encode(self, key, observation, deltas):
        body = json.dumps({'observation':observation,'deltas':deltas},ensure_ascii=False)
        if len(body.encode()) > 262144:
            raise ValueError('visual checkpoint exceeds bound')
        return json.dumps({'body':body,'mac':hmac.new(self.secret,(key+body).encode(),hashlib.sha256).hexdigest()})

    def decode(self, key, value):
        if not value: return None
        try:
            data=json.loads(value)
            body=data['body']
            if len(body.encode())>262144 or not hmac.compare_digest(data['mac'],hmac.new(self.secret,(key+body).encode(),hashlib.sha256).hexdigest()):
                return None
            result=json.loads(body)
            if not isinstance(result['observation'],str) or not isinstance(result['deltas'],list) or not all(isinstance(d,str) for d in result['deltas']):
                return None
            return result
        except (ValueError,KeyError,TypeError,AttributeError):
            return None

    def load(self, key):
        if key is None: return None
        from redis import Redis
        with Redis.from_url(self.url,socket_timeout=5) as client:
            return self.decode(key,client.get(key))

    def save(self, key, observation, deltas):
        if key is None: return
        from redis import Redis
        with Redis.from_url(self.url,socket_timeout=5) as client:
            client.set(key,self.encode(key,observation,deltas),ex=self.ttl)
