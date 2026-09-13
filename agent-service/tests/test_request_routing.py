from unittest.mock import Mock
import json
import time
import pytest
from app.runtime.routing import general_route, is_search_request, compose_spaces, compose_space_usage
from app.runtime.java_client import TaskContext, AccessibleSpace
from app.runtime.runner import TaskRunner
from app.security.service_token import ServiceContext


@pytest.mark.parametrize('query', ['我有权限查看的项目空间有哪些', '列出我可以访问的空间', '我有哪些空间'])
def test_space_route(query):
    assert general_route(query) == 'accessible_spaces'


def test_picture_request_not_replaced_by_directory():
    assert general_route('查找我有权限的空间中的图片') is None
    assert is_search_request('查找我有权限的空间中的图片')
    assert not is_search_request('明天天气怎么样')


@pytest.mark.parametrize('query,expected', [
    ('我有权限查看的项目空间有哪些', '实验室空间'),
    ('分析一下我被授权空间的使用情况', '空间使用情况'),
    ('你能做什么', '我可以'),
    ('明天天气怎么样', '不会自动搜索'),
])
def test_non_picture_questions_never_call_retrieval_or_vision(query, expected):
    java = Mock()
    context = TaskContext(taskId='t', conversationId='c', userId='7', spaceId=None,
                          query=query, status='PENDING')
    java.get_context.side_effect = lambda *a: context.model_copy(update={'status': 'PENDING' if java.get_context.call_count == 1 else 'RUNNING'})
    java.get_accessible_spaces.return_value = [AccessibleSpace(spaceName='实验室空间', spaceType=1, permissions=['picture:view'])]
    executor, vision = Mock(), Mock()
    signed = ServiceContext(task_id='t', conversation_id='c', user_id='7', space_id=None,
                            issued_at=int(time.time()), expires_at=int(time.time())+300)
    TaskRunner(java, executor, vision).run(signed, 'token')
    executor.execute.assert_not_called()
    vision.analyze.assert_not_called()
    vision.analyze_stream.assert_not_called()
    assert java.update_state.call_args.kwargs['status'] == 'SUCCEEDED'
    payloads = ' '.join(str(c) for c in java.append_event.call_args_list)
    # Decode escaped JSON to inspect the user-facing answer.
    answers = [json.loads(c.args[3]) for c in java.append_event.call_args_list if c.args[2]=='answer_delta']
    assert expected in str(answers)


def test_empty_spaces_is_not_empty_picture_search():
    assert '没有可查看' in compose_spaces([])


@pytest.mark.parametrize('query', ['分析一下我被授权空间的使用情况', '看看我有权限的空间占用多少容量', '我的空间用量', '我能访问的空间有多少图片'])
def test_authorized_usage_route(query):
    assert general_route(query) == 'accessible_space_usage'


@pytest.mark.parametrize('query', ['统计当前空间图片数量', '查找我有权限的空间的图片', '比较空间 1、2', '我被授权空间最近的上传趋势'])
def test_usage_does_not_override_other_scopes_or_tasks(query):
    assert general_route(query) != 'accessible_space_usage'


def test_usage_totals_and_capacity_warning():
    space = AccessibleSpace(spaceName='实验室', spaceType=1, permissions=['picture:view'],
                            totalCount=8, maxCount=10, totalSize=1024, maxSize=2048)
    result = compose_space_usage([space])
    assert '8 / 10' in result
    assert '50.0%' in result
    assert '1.00 KiB' in result
    assert '80%' in result
    assert '不含公共图库' in result


def test_unknown_usage_not_reported_as_zero():
    space = AccessibleSpace(spaceName='旧接口', permissions=['picture:view'])
    assert '未知' in compose_space_usage([space])
    assert '未将未知值当作零' in compose_space_usage([space])
    assert '暂无空间使用情况' in compose_space_usage([])
