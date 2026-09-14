import json
from unittest.mock import Mock
import pytest
from langgraph.checkpoint.memory import InMemorySaver
from app.graph.workflow import LangGraphWorkflow
from app.runtime.java_client import TaskContext, PictureCandidate
from app.runtime.task_checkpoint import TaskStepStore
from app.runtime.runner import TaskRunner
from app.retrieval.keyword_executor import ExecutionResult
from test_task_runtime import settings


def context():
    return TaskContext(taskId='t',conversationId='c',userId='7',spaceId='9',query='查找图片',status='PENDING')


def test_same_task_completed_retrieval_is_reauthorized_and_reused():
    executor=Mock()
    executor.execute_with_state.return_value=ExecutionResult('已查到',[{'pictureId':'1'}],1)
    graph=LangGraphWorkflow(executor,InMemorySaver())
    authorize=Mock(return_value=[PictureCandidate(pictureId='1',spaceId='9')])
    graph.execute(context(),Mock(),authorize,lambda:None)
    result=graph.execute(context(),Mock(),authorize,lambda:None)
    assert result.answer=='已查到'
    assert executor.execute_with_state.call_count==1
    authorize.assert_called_once_with(['1'])
    authorize.return_value=[]
    with pytest.raises(ValueError):graph.execute(context(),Mock(),authorize,lambda:None)
    assert executor.execute_with_state.call_count==1
    graph.execute(context().model_copy(update={'taskId':'new-turn'}),Mock(),authorize,lambda:None)
    assert executor.execute_with_state.call_count==2


def test_checkpoint_signature_binding_and_ttl():
    client=Mock()
    store=TaskStepStore(settings(),client)
    key=store.key(context(),'plan',{})
    store.save(key,{'task':'search'})
    assert client.set.call_args.kwargs['ex']>0
    client.get.return_value=client.set.call_args.args[1]
    assert store.load(key)=={'task':'search'}
    assert store.load(store.key(context().model_copy(update={'userId':'8'}),'plan',{})) is None
    envelope=json.loads(client.get.return_value);envelope['body']='{}'
    client.get.return_value=json.dumps(envelope)
    assert store.load(key) is None


def test_summary_resume_skips_model_but_not_active_check():
    store=Mock();store.load.return_value={'summary':'pictureId=1 摘要'}
    vision=Mock()
    runner=TaskRunner(Mock(),Mock(),vision,task_checkpoint=store)
    check=Mock()
    assert runner._resume_visual_summary(context(),['观察'],['1'],check)=='pictureId=1 摘要'
    assert check.call_count==2
    vision.summarize.assert_not_called()
    check.side_effect=RuntimeError('cancelled')
    with pytest.raises(RuntimeError):runner._resume_visual_summary(context(),['观察'],['1'],check)


def test_failed_summary_is_not_cached():
    store=Mock();store.load.return_value=None
    vision=Mock();vision.summarize.return_value=None
    runner=TaskRunner(Mock(),Mock(),vision,task_checkpoint=store)
    assert runner._resume_visual_summary(context(),['观察'],['1'],lambda:None) is None
    store.save.assert_not_called()
