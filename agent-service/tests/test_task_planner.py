import json
from dataclasses import replace
from unittest.mock import Mock
import httpx
import pytest
from app.runtime.planner import TaskPlan, TaskPlanner, fallback_plan
from app.runtime.java_client import TaskContext
from test_task_runtime import settings


def context(query='查找河道图片', **kw):
    return TaskContext(taskId='t', conversationId='c', userId='7', spaceId=None,
                       status='PENDING', query=query, **kw)


def planner(outputs):
    calls = []
    def handler(request):
        calls.append(json.loads(request.content))
        value = outputs[min(len(calls)-1, len(outputs)-1)]
        return httpx.Response(200, json={'choices':[{'message':{'content':json.dumps(value)}}]})
    return TaskPlanner(replace(settings(), dashscope_api_key='test-only'),
                       httpx.Client(base_url='https://test', transport=httpx.MockTransport(handler))), calls


def test_search_is_not_automatic_visual_analysis():
    assert not fallback_plan(context()).visualAnalysis
    assert fallback_plan(context('查找河道图片并分析可见差异')).visualAnalysis


@pytest.mark.parametrize('query', ['你好', '我能访问哪些空间', '分析我被授权空间使用情况', '批量删除图片'])
def test_fallback_non_search(query):
    assert fallback_plan(context(query)).task != 'search'


def test_model_routes_paraphrase():
    p, calls = planner([{'task':'accessible_space_usage', 'confidence':.95}])
    assert p.plan(context('看看获准访问的项目还剩多少存储')).task == 'accessible_space_usage'
    assert len(calls) == 1


@pytest.mark.parametrize('output', [
    {'task':'delete'}, {'task':'search','spaceId':'999'},
    {'task':'search','visualAnalysis':'false'}, {'task':'search','confidence':2},
])
def test_invalid_plan_bounded_repair(output):
    p, calls = planner([output])
    assert p.plan(context()).task == 'clarify'
    assert len(calls) == 2


@pytest.mark.parametrize('output', [
    {'task':'search','needsScopeSelection':True},
    {'task':'search','confidence':.3}, {'task':'picture_analysis'},
    {'task':'picture_group_analysis'}, {'task':'temporary_image_analysis'},
])
def test_missing_input_or_scope_never_guessed(output):
    p, _ = planner([output])
    assert p.plan(context()).task == 'clarify'


def test_nonvisual_tools_cannot_request_images():
    p, _ = planner([{'task':'accessible_spaces','visualAnalysis':True}])
    assert not p.plan(context()).visualAnalysis


def test_cancellation_not_swallowed():
    p, _ = planner([{'task':'search'}])
    def cancelled(): raise RuntimeError('cancelled')
    with pytest.raises(RuntimeError): p.plan(context(), cancelled)


@pytest.mark.parametrize('query,name', [('恢复全部授权空间','全部授权空间'),('只看公共图库','公共图库')])
def test_explicit_scope_controls_do_not_depend_on_model(query,name):
    p,calls=planner([{'task':'clarify'}])
    result=p.plan(context(query))
    assert result.task=='search' and result.scopeName==name
    assert not calls
