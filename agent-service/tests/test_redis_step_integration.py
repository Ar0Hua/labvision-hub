"""Opt-in real Redis test. Uses isolated keys and public fixture data, not application credentials."""
import os
import subprocess
import sys
import uuid
import pytest


@pytest.mark.skipif(not os.getenv('LABVISION_TEST_REDIS_URL'),reason='real Redis integration URL not configured')
def test_completed_step_survives_process_exit():
    from redis import Redis
    url=os.environ['LABVISION_TEST_REDIS_URL']
    task=uuid.uuid4().hex
    # Separate interpreter processes ensure the observed value is not process-local memory.
    script='''
import os,sys
from types import SimpleNamespace
from app.runtime.task_checkpoint import TaskStepStore
from app.runtime.java_client import TaskContext
s=SimpleNamespace(checkpoint_redis_url=os.environ['LABVISION_TEST_REDIS_URL'],
    service_secret='public-integration-fixture-secret-12345',checkpoint_ttl_minutes=1,
    chat_model='fixture',vision_model='fixture')
store=TaskStepStore(s)
c=TaskContext(taskId=sys.argv[1],conversationId='integration',userId='7',spaceId=None,
    query='fixture',status='PENDING')
key=store.key(c,'integration-step',{})
if sys.argv[2]=='write':
    store.save(key,{'task':'search'})
    print(key)
else:
    assert store.load(key)=={'task':'search'}
    print('RESTORED')
'''
    written=subprocess.run([sys.executable,'-c',script,task,'write'],capture_output=True,text=True,check=True,timeout=20)
    key=written.stdout.strip()
    assert key.startswith('labvision:task-step:')
    try:
        read=subprocess.run([sys.executable,'-c',script,task,'read'],capture_output=True,text=True,check=True,timeout=20)
        assert read.stdout.strip()=='RESTORED'
        with Redis.from_url(url) as client:assert 0<client.ttl(key)<=60
    finally:
        with Redis.from_url(url) as client:client.delete(key)
