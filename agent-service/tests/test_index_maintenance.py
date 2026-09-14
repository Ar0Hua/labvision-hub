from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from app.indexing.maintenance import run_page, needs_repair


def row():
    return dict(pictureId='9',isDelete=0,spaceId=None,reviewStatus=1,sourceUpdatedAtEpoch=100,indexStatus='READY',embeddingVersion='v1')


def test_reconcile_current_missing_stale_deleted():
    current={'payload':dict(sourceUpdatedAtEpoch=100,scopeKey='public',reviewStatus=1,isDelete=0)}
    assert not needs_repair(row(),current,'v1')
    assert needs_repair(row(),None,'v1')
    assert needs_repair(row(),current,'v2')
    assert needs_repair(dict(row(),sourceUpdatedAtEpoch=101),current,'v1')
    assert needs_repair(dict(row(),isDelete=1),current,'v1')
    assert not needs_repair(dict(row(),isDelete=1),None,'v1')


def test_backfill_cursor_only_after_success_and_idempotent_run():
    worker=Mock()
    worker._java_call.side_effect=[[row()],RuntimeError('offline')]
    state={'after':0,'runId':'same-run','complete':False}
    with pytest.raises(RuntimeError):run_page(worker,state,'backfill',1)
    assert state['after']==0
    worker._java_call.side_effect=[[row()],1]
    result,count=run_page(worker,state,'backfill',1)
    assert result['after']==9 and count==1 and not result['complete']
    assert worker._java_call.call_args.kwargs['params']['runId']=='same-run'


def test_bad_cursor_rejected_before_enqueue():
    worker=Mock()
    worker._java_call.return_value=[row()]
    with pytest.raises(ValueError):run_page(worker,{'after':9,'runId':'r'},'backfill',10)
    assert worker._java_call.call_count==1


def test_qdrant_failure_does_not_enqueue_or_advance():
    worker=Mock()
    worker._settings=SimpleNamespace(qdrant_collection='pictures',feature_version='v1')
    worker._java_call.return_value=[row()]
    worker._qdrant.post.return_value.raise_for_status.side_effect=RuntimeError('offline')
    state={'after':0,'runId':'r'}
    with pytest.raises(RuntimeError):run_page(worker,state,'reconcile',10)
    assert state['after']==0 and worker._java_call.call_count==1
