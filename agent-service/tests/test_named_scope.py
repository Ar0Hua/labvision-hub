from types import SimpleNamespace
import pytest
from app.runtime.java_client import TaskContext, AccessibleSpace
from app.runtime.scope import resolve_scope, validate_scope, matches_scope
from app.graph.workflow import LangGraphWorkflow
from app.retrieval.keyword_executor import ExecutionResult
from langgraph.checkpoint.memory import InMemorySaver


def context(**extra):
    return TaskContext(taskId='t',conversationId='c',userId='7',spaceId=None,allSpaces=True,
                       allowedSpaceIds=['9'],query='查找图片',status='PENDING',**extra)


def test_name_resolution_never_guesses_or_broadens():
    spaces=[AccessibleSpace(spaceId='9',spaceName='实验室',permissions=['picture:view'])]
    assert resolve_scope(context(),'实验室',spaces)=='space:9'
    with pytest.raises(ValueError):resolve_scope(context(),'不存在',spaces)
    with pytest.raises(ValueError):resolve_scope(context(),'实验室',spaces*2)
    with pytest.raises(ValueError):validate_scope(context(),'space:10')
    assert not matches_scope(SimpleNamespace(spaceId='10'),'space:9')


def test_multiturn_scope_retained_and_reset_without_old_results():
    calls=[]
    class Executor:
        def execute_with_state(self,ctx,search,authorize,check,previous,ids):
            calls.append((ctx.searchScope,previous,ids))
            return ExecutionResult('ok',[],0,{'example':'memory'})
    graph=LangGraphWorkflow(Executor(),InMemorySaver())
    a=context(searchScope='space:9')
    graph.execute(a,lambda *a:[],lambda *a:[],lambda:None)
    graph.execute(a.model_copy(update={'taskId':'t2','searchScope':None}),lambda *a:[],lambda *a:[],lambda:None)
    assert calls[-1][0]=='space:9' and calls[-1][1]=={'example':'memory'}
    graph.execute(a.model_copy(update={'taskId':'t3','searchScope':'all'}),lambda *a:[],lambda *a:[],lambda:None)
    assert calls[-1]==('all',{'example':'memory'},[])


def test_revoked_persisted_scope_rejected_before_executor():
    with pytest.raises(ValueError):validate_scope(context().model_copy(update={'allowedSpaceIds':[]}), 'space:9')
