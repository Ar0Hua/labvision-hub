from unittest.mock import Mock, patch
from types import SimpleNamespace
import pytest
from app.indexing.lifecycle import switch
from app.indexing.scheduler import sweep_page


def manager(points=10,status='green'):
    m=Mock()
    aliases=Mock();aliases.json.return_value={'result':{'aliases':[{'alias_name':'live','collection_name':'v1'}]}}
    target=Mock();target.json.return_value={'result':{'status':status,'points_count':points}}
    m._client.get.side_effect=[aliases,target]
    return m


def test_alias_preview_is_read_only():
    m=manager()
    assert not switch(m,'live','v1','v2',10)['applied']
    m._client.post.assert_not_called()


def test_alias_atomic_switch_keeps_collections():
    m=manager()
    assert switch(m,'live','v1','v2',10,True)['applied']
    actions=m._client.post.call_args.kwargs['json']['actions']
    assert actions==[{'delete_alias':{'alias_name':'live'}},{'create_alias':{'alias_name':'live','collection_name':'v2'}}]
    m._client.delete.assert_not_called()


@pytest.mark.parametrize('points,status',[(0,'green'),(10,'red')])
def test_unready_target_cannot_switch(points,status):
    m=manager(points,status)
    with pytest.raises(ValueError):switch(m,'live','v1','v2',10,True)
    m._client.post.assert_not_called()


def test_completed_daily_sweep_not_repeated(tmp_path):
    worker=Mock()
    worker._settings=SimpleNamespace(qdrant_collection='v1',feature_version='f1',java_base_url='http://java',qdrant_url='http://qd')
    def page(_,state,*args):return dict(state,after=10,complete=True),1
    with patch('app.indexing.scheduler.run_page',side_effect=page) as run:
        assert sweep_page(worker,tmp_path,'2026-09-14')['queued']==1
        assert sweep_page(worker,tmp_path,'2026-09-14')['queued']==0
        assert run.call_count==1
        sweep_page(worker,tmp_path,'2026-09-15')
        assert run.call_count==2
