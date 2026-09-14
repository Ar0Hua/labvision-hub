from unittest.mock import Mock
import pytest
from app.runtime.composite import CompositeWorkflow
from app.runtime.planner import TaskPlan, fallback_plan
from app.runtime.java_client import PictureCandidate
from app.retrieval.keyword_executor import ExecutionResult, KeywordSearchExecutor
from test_task_planner import context, planner


def picture(i, **kw):
    return PictureCandidate(pictureId=str(i), spaceId=None, category='原始数据', **kw)


def result(ids, **kw):
    return ExecutionResult('', [{'pictureId': str(i)} for i in ids], len(ids),
                           {'searchText': '河道', 'category': '原始数据', **kw})


def run(pages, target=3, authorize=None, check=lambda: None):
    events, calls = [], []
    def supplement(intent):
        calls.append(intent)
        return pages[min(len(calls), len(pages)-1)]
    output = CompositeWorkflow().execute(context(), TaskPlan(task='search_group_analysis', targetCount=target),
        lambda: pages[0], supplement,
        authorize or (lambda ids: [picture(i) for i in ids]), check,
        lambda stage, data: events.append((stage, data)))
    return output, events, calls


def test_complete_loop_supplements_without_relaxing_filters():
    output, events, calls = run([result([1, 2]), result([3])])
    assert [p.pictureId for p in output.pictures] == ['1', '2', '3']
    assert calls[0]['category'] == '原始数据'
    assert calls[0]['excludePictureIds'] == ['1', '2']
    assert [s for s, _ in events] == ['RETRIEVE','FILTER','GROUP_ANALYSIS','EVIDENCE_CHECK',
                                      'SUPPLEMENT','FILTER','GROUP_ANALYSIS','EVIDENCE_CHECK']
    assert events[-1][1]['sufficient']


def test_sufficient_evidence_skips_supplement():
    output, _, calls = run([result([1, 2, 3])])
    assert not calls and output.result.candidate_count == 3


def test_no_progress_stops_and_preserves_partial_results():
    output, _, calls = run([result([1, 2])])
    assert len(calls) == 1
    assert '未产生新结果' in output.result.answer
    assert '证据不完整' in output.result.answer


def test_at_most_two_supplements():
    output, _, calls = run([result([1]),result([2]),result([3])], target=10)
    assert len(calls) == 2 and output.rounds == 3


def test_final_permission_revocation_removes_evidence():
    count = 0
    def authorize(ids):
        nonlocal count
        count += 1
        return [picture(i) for i in ids if count < 3 or i != '2']
    output, _, _ = run([result([1, 2, 3])], authorize=authorize)
    assert '2' not in [c['pictureId'] for c in output.result.citations]
    assert '图片 ID: 2' not in output.result.answer


def test_broker_extra_ids_and_wrong_scope_are_rejected():
    output, _, _ = run([result([1, 2])], target=2,
        authorize=lambda ids: [picture(1), PictureCandidate(pictureId='2', spaceId='9'), picture(99)])
    assert '99' not in [p.pictureId for p in output.pictures]
    assert '2' not in [p.pictureId for p in output.pictures]


def test_runner_wires_composite_flow_and_streams_result():
    from app.runtime.runner import TaskRunner
    from app.security.service_token import ServiceContext
    java = Mock()
    ctx = context()
    java.get_context.side_effect = lambda *args: ctx.model_copy(update={'status': 'RUNNING' if java.update_state.called else 'PENDING'})
    java.authorize_pictures.side_effect = lambda task, token, ids: [picture(i) for i in ids]
    executor, extra, router = Mock(), Mock(), Mock()
    executor.execute.return_value = result([1])
    extra.execute_with_state.return_value = result([2])
    router.plan.return_value = TaskPlan(task='search_group_analysis', targetCount=2)
    runner = TaskRunner(java, executor, planner=router, composite_executor=extra)
    runner.run(ServiceContext('t','c','7',None,1,301), 'token')
    assert java.update_state.call_args.kwargs['status'] == 'SUCCEEDED'
    assert [c.kwargs['status'] for c in java.update_state.call_args_list] == ['RUNNING', 'SUCCEEDED']
    events = [args.args for args in java.append_event.call_args_list]
    assert any(e[2] == 'answer_delta' and '检索与分组分析' in e[3] for e in events)
    assert any(e[2] == 'tool_result' and 'EVIDENCE_CHECK' in e[3] for e in events)
    extra.execute_with_state.assert_called_once()


def test_cancellation_propagates():
    def cancel(): raise RuntimeError('cancelled')
    with pytest.raises(RuntimeError, match='cancelled'):
        run([result([1])], check=cancel)


def test_missing_intent_never_reconstructs_or_broadens_query():
    output, _, calls = run([ExecutionResult('', [{'pictureId':'1'}], 1)])
    assert not calls and '未自动放宽条件' in output.result.answer


def test_planner_accepts_search_then_group_without_selected_images():
    p, _ = planner([{'task':'search_group_analysis', 'targetCount':4, 'groupBy':'space', 'visualAnalysis':True}])
    plan = p.plan(context('找河道图片，筛选后按项目分组并比较'))
    assert plan.task == 'search_group_analysis' and plan.groupBy == 'space'
    assert fallback_plan(context('查找河道并分组')).task == 'search_group_analysis'


@pytest.mark.parametrize('value', [1, 21, 100])
def test_plan_rejects_unbounded_sample_size(value):
    with pytest.raises(ValueError): TaskPlan(task='search_group_analysis', targetCount=value)


def test_supplement_uses_frozen_intent_not_a_second_model_parse():
    parser = Mock()
    search = Mock(return_value=[])
    KeywordSearchExecutor(parser).execute_with_state(context(), search, lambda ids: [], lambda:None,
        None, [], frozen_intent={'searchText':'河道','category':'原始数据','excludePictureIds':['1']})
    parser.parse.assert_not_called()
    assert search.call_args.args[4]['excludePictureIds'] == ['1']


def test_inherited_scope_is_preserved_in_supplements():
    ctx = context(allSpaces=True, allowedSpaceIds=['9'])
    def retrieve():
        ctx.searchScope = 'space:9'
        return result([1])
    calls=[]
    def supplement(intent):
        calls.append(ctx.searchScope)
        return result([2])
    output = CompositeWorkflow().execute(ctx, TaskPlan(task='search_group_analysis',targetCount=2),
        retrieve, supplement, lambda ids: [PictureCandidate(pictureId=i,spaceId='9',category='原始数据') for i in ids],
        lambda: None, lambda *args: None)
    assert calls == ['space:9'] and len(output.pictures)==2
