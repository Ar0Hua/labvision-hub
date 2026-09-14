from dataclasses import replace
import json
from app.runtime.visual_checkpoint import VisualBatchCheckpoint
from app.runtime.java_client import TaskContext, VisionInput
from test_task_runtime import settings
from unittest.mock import Mock
from types import SimpleNamespace
from app.runtime.runner import TaskRunner
from app.retrieval.keyword_executor import ExecutionResult


def test_cache_bound_to_user_task_source_and_model_not_url_signature():
    store=VisualBatchCheckpoint(settings())
    context=TaskContext(taskId='t',conversationId='c',userId='7',spaceId=None,status='PENDING',query='分析')
    pic=VisionInput(pictureId='1',spaceId=None,sourceVersion='100',temporaryUrl='https://cos.example/a?sig=1',expiresInSeconds=120)
    key=store.key(context,[pic])
    assert key==store.key(context,[pic.model_copy(update={'temporaryUrl':'https://cos.example/a?sig=2'})])
    assert key!=store.key(context.model_copy(update={'userId':'8'}),[pic])
    assert key!=store.key(context,[pic.model_copy(update={'sourceVersion':'101'})])
    assert store.key(context,[pic.model_copy(update={'sourceVersion':None})]) is None
    encoded=store.encode(key,'pictureId=1 合法观察',['pictureId=1 合法观察'])
    assert 'https://' not in encoded
    assert store.decode(key,encoded)['observation']=='pictureId=1 合法观察'
    assert store.decode(key+'other',encoded) is None
    tampered=json.loads(encoded);tampered['body']='{}'
    assert store.decode(key,json.dumps(tampered)) is None


def test_retry_reauthorizes_before_reusing_completed_batch():
    store=Mock()
    store.key.return_value='key'
    store.load.return_value={'observation':'pictureId=1 河道','deltas':['pictureId=1 河道']}
    java=Mock()
    java.get_vision_inputs.return_value=[VisionInput(pictureId='1',spaceId=None,sourceVersion='100',
        temporaryUrl='https://cos.example/a',expiresInSeconds=120)]
    vision=Mock(max_pictures=4)
    vision.summarize.return_value=None
    runner=TaskRunner(java,Mock(),vision,visual_checkpoint=store)
    ctx=TaskContext(taskId='t',conversationId='c',userId='7',spaceId=None,status='PENDING',query='分析')
    output=runner._stream_visual_batches(ExecutionResult('结果',[],1),ctx,SimpleNamespace(task_id='t'),
                                        'token',lambda:None,lambda _:None,['1'])
    java.get_vision_inputs.assert_called_once_with('t','token',['1'])
    vision.analyze_stream.assert_not_called()
    assert 'pictureId=1 河道' in output.answer
    java.get_vision_inputs.return_value=[]
    import pytest
    with pytest.raises(ValueError):
        runner._stream_visual_batches(ExecutionResult('结果',[],1),ctx,SimpleNamespace(task_id='t'),
                                     'token',lambda:None,lambda _:None,['1'])
    assert store.load.call_count==1
