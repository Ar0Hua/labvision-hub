import pytest
from unittest.mock import Mock
from langgraph.checkpoint.memory import InMemorySaver
from app.graph.workflow import LangGraphWorkflow
from app.runtime.followup import parse_reference, resolve_reference, FollowupClarification
from app.runtime.java_client import PictureCandidate
from app.runtime.runner import TaskRunner
from app.security.service_token import ServiceContext
from test_task_planner import context


def auth(ids):
    return [PictureCandidate(pictureId=i,spaceId=None,category='原图') for i in reversed(ids)]


@pytest.mark.parametrize('query,count,ordinal',[
    ('把刚才前10张按项目分组',10,False),('分析上一轮第2张',2,True),
    ('解释刚刚第二张',2,True),('把上轮前十张按分类分组',10,False)])
def test_parse(query,count,ordinal):
    ref=parse_reference(query)
    assert (ref.count,ref.ordinal)==(count,ordinal)


def test_order_is_resolved_before_authorization_and_never_reordered():
    ctx=context()
    plan=resolve_reference(ctx,parse_reference('把刚才前3张按项目分组'),
        {'pictureIds':['7','3','9'],'scope':None},auth)
    assert ctx.examplePictureIds==['7','3','9']
    assert plan.task=='picture_group_analysis' and plan.groupBy=='space'
    resolve_reference(ctx,parse_reference('分析上一轮第2张'),{'pictureIds':['7','3','9']},auth)
    assert ctx.examplePictureIds==['3']


@pytest.mark.parametrize('query', ['分析上一轮第0张','把刚才前21张按项目分组','分析上一轮图片',
    '对比上一轮第1张和第2张','分析上一轮第2张并修改标签'])
def test_ambiguous_or_unsupported_reference_clarifies(query):
    with pytest.raises(FollowupClarification):parse_reference(query)


def test_no_history_out_of_range_revocation_do_not_substitute():
    ref=parse_reference('分析上一轮第2张')
    for snapshot,authorize in [(None,auth),({'pictureIds':['1']},auth),
        ({'pictureIds':['1','2','3']},lambda ids:auth(['3']))]:
        with pytest.raises(FollowupClarification):resolve_reference(context(),ref,snapshot,authorize)


def test_snapshot_isolation_final_results_and_retry_binding():
    flow=LangGraphWorkflow(Mock(),InMemorySaver())
    first=context().model_copy(update={'taskId':'first'})
    second=context().model_copy(update={'taskId':'second'})
    flow.remember_result(first,[{'pictureId':'8'},{'pictureId':'2'}])
    assert flow.previous_result(second)['pictureIds']==['8','2']
    flow.remember_result(second,[{'pictureId':'2'}])
    # Same-task retry must still refer to first task, not its own output.
    assert flow.previous_result(second)['pictureIds']==['8','2']
    assert flow.previous_result(context().model_copy(update={'taskId':'third'}))['pictureIds']==['2']
    assert flow.previous_result(second.model_copy(update={'userId':'99'})) is None
    assert flow.previous_result(second.model_copy(update={'conversationId':'other'})) is None
    flow.remember_result(second,[])
    assert flow.previous_result(context().model_copy(update={'taskId':'third'}))['pictureIds']==[]


@pytest.mark.parametrize('query,ids', [('分析上一轮第2张',['2']),('把刚才前3张按项目分组',['1','2','3'])])
def test_runner_history_to_analysis_does_not_search_or_call_planner(query,ids):
    ctx=context(query)
    java,executor,planner=Mock(),Mock(),Mock()
    java.get_context.side_effect=lambda *args:ctx.model_copy(update={'status':'RUNNING' if java.update_state.called else 'PENDING'})
    java.authorize_pictures.side_effect=lambda task,token,values: auth(values)
    java.get_accessible_spaces.return_value=[]
    executor.previous_result.return_value={'pictureIds':['1','2','3'],'scope':None}
    runner=TaskRunner(java,executor,planner=planner)
    runner.run(ServiceContext('t','c','7',None,1,301),'token')
    assert java.update_state.call_args.kwargs['status']=='SUCCEEDED'
    executor.execute.assert_not_called()
    planner.plan.assert_not_called()
    assert [c['pictureId'] for c in executor.remember_result.call_args.args[1]]==ids


def test_search_followup_is_not_silently_treated_as_analysis():
    assert parse_reference('找更像上一轮第2张的图片') is None


def test_narrow_scope_cannot_be_crossed():
    ctx=context(allSpaces=True,allowedSpaceIds=['9'])
    with pytest.raises(FollowupClarification):
        resolve_reference(ctx,parse_reference('分析上一轮第2张'),
            {'pictureIds':['1','2'],'scope':'space:9'},auth)
