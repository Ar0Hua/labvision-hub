import pytest
from pydantic import ValidationError
from app.evaluation.acceptance import AcceptanceEvidence, assess


def evidence():
    ids=[str(i) for i in range(1,11)]
    return dict(source='measured',humanReviewed=True,datasetVersion='unit-fixture-not-real',codeVersion='fixture',
                modelVersion='fixture',capturedAt='2026-09-14',
                queries=[dict(queryId=str(i),relevantPictureIds=ids,allowedPictureIds=ids,rankedPictureIds=ids) for i in range(20)],
                latencySeconds={key:[1.0]*20 for key in ('retrieval','firstAnswer','searchTotal','singleAnalysis')},
                indexDelaySeconds=[10.0]*20,toolAttempts=100,toolSucceeded=100,permissionChecks=20,permissionLeaks=0)


def test_gate_calculation_fixture_is_not_live_validation():
    assert assess(AcceptanceEvidence(**evidence()))['passed']


@pytest.mark.parametrize('change',[{'source':'mock'},{'humanReviewed':False},{'queries':[]},
                                  {'indexDelaySeconds':[float('nan')]*20},{'toolSucceeded':101}])
def test_mock_missing_or_invalid_measurements_rejected(change):
    with pytest.raises(ValidationError):AcceptanceEvidence(**(evidence()|change))


def test_missing_metric_or_leak_fails_gate():
    data=evidence();data['latencySeconds'].pop('firstAnswer');data['permissionLeaks']=1
    result=assess(AcceptanceEvidence(**data))
    assert not result['passed']
    assert 'permissionLeakage' in result['failedChecks']
    assert 'firstAnswer:missing' in result['failedChecks']


def test_out_of_scope_result_fails_even_if_relevance_is_good():
    data=evidence();data['queries'][0]['rankedPictureIds']=[*data['queries'][0]['rankedPictureIds'],'999']
    assert 'permissionLeakage' in assess(AcceptanceEvidence(**data))['failedChecks']
