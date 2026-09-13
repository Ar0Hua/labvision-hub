from unittest.mock import Mock
import json
import time
import pytest
from app.runtime.routing import general_route, is_search_request, compose_spaces
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
