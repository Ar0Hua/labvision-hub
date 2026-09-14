"""Bounded signed task steps. Values contain no credentials, URLs, or hidden model reasoning."""
import hashlib
import hmac
import json


class TaskStepStore:
    MAX_BYTES = 262144

    def __init__(self, settings, client=None):
        self.url, self.secret = settings.checkpoint_redis_url, settings.service_secret.encode()
        self.ttl = settings.checkpoint_ttl_minutes * 60
        self.models = [settings.chat_model, settings.vision_model]
        self.client = client

    def key(self, context, stage, dependencies):
        binding = [context.userId,context.conversationId,context.taskId,context.query,
                   context.spaceId,context.allSpaces,context.allowedSpaceIds,
                   context.examplePictureIds,context.temporaryImageId,self.models,stage,dependencies]
        body=json.dumps(binding,sort_keys=True,ensure_ascii=False,default=str)
        return 'labvision:task-step:'+hashlib.sha256(body.encode()).hexdigest()

    def _mac(self,key,body):
        return hmac.new(self.secret,(key+body).encode(),hashlib.sha256).hexdigest()

    def load(self,key):
        if self.client is None:
            from redis import Redis
            with Redis.from_url(self.url,socket_timeout=5) as client:
                raw=client.get(key)
        else: raw=self.client.get(key)
        if not raw or len(raw)>self.MAX_BYTES*2:return None
        try:
            envelope=json.loads(raw)
            body=envelope['body']
            if len(body.encode())>self.MAX_BYTES or not hmac.compare_digest(envelope['mac'],self._mac(key,body)):
                return None
            return json.loads(body)
        except (ValueError,TypeError,KeyError,AttributeError):return None

    def save(self,key,value):
        body=json.dumps(value,ensure_ascii=False,allow_nan=False)
        if len(body.encode())>self.MAX_BYTES:raise ValueError('task checkpoint too large')
        envelope=json.dumps({'body':body,'mac':self._mac(key,body)},ensure_ascii=False)
        if self.client is None:
            from redis import Redis
            with Redis.from_url(self.url,socket_timeout=5) as client:
                client.set(key,envelope,ex=self.ttl)
        else:self.client.set(key,envelope,ex=self.ttl)
