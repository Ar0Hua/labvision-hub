"""Evaluate explicit measured acceptance evidence, never substitute mock contract results."""
import argparse
import json
import math
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.evaluation.retrieval import GoldenCase, Prediction, evaluate


class MeasuredQuery(BaseModel):
    model_config=ConfigDict(extra='forbid')
    queryId: str = Field(min_length=1)
    relevantPictureIds: list[str] = Field(min_length=1)
    allowedPictureIds: list[str]
    rankedPictureIds: list[str]

    @model_validator(mode='after')
    def validate_labels(self):
        GoldenCase(queryId=self.queryId,relevantPictureIds=self.relevantPictureIds)
        Prediction(queryId=self.queryId,rankedPictureIds=self.rankedPictureIds)
        if not set(self.relevantPictureIds)<=set(self.allowedPictureIds):raise ValueError('relevant labels exceed permission scope')
        return self


class AcceptanceEvidence(BaseModel):
    model_config=ConfigDict(extra='forbid')
    source: Literal['measured']
    humanReviewed: Literal[True]
    datasetVersion: str = Field(min_length=1)
    codeVersion: str = Field(min_length=1)
    modelVersion: str = Field(min_length=1)
    capturedAt: str = Field(min_length=1)
    queries: list[MeasuredQuery] = Field(min_length=20)
    latencySeconds: dict[str,list[float]]
    indexDelaySeconds: list[float] = Field(min_length=20)
    toolAttempts: int = Field(ge=20)
    toolSucceeded: int = Field(ge=0)
    permissionChecks: int = Field(ge=20)
    permissionLeaks: int = Field(ge=0)

    @model_validator(mode='after')
    def valid_measurements(self):
        if self.toolSucceeded>self.toolAttempts:raise ValueError('invalid tool counts')
        if len({q.queryId for q in self.queries})!=len(self.queries):raise ValueError('duplicate query IDs')
        for values in [*self.latencySeconds.values(),self.indexDelaySeconds]:
            if len(values)<20 or any(not math.isfinite(x) or x<0 for x in values):
                raise ValueError('need at least 20 finite nonnegative measurements per series')
        return self


def p95(values):
    return sorted(values)[math.ceil(len(values)*.95)-1]


def assess(evidence):
    golden=[GoldenCase(queryId=q.queryId,relevantPictureIds=q.relevantPictureIds,
                      forbiddenPictureIds=sorted(set(q.rankedPictureIds)-set(q.allowedPictureIds))) for q in evidence.queries]
    predictions=[Prediction(queryId=q.queryId,rankedPictureIds=q.rankedPictureIds) for q in evidence.queries]
    metrics=evaluate(golden,predictions)
    failures=[]
    for key,threshold in {'recallAt20':.85,'precisionAt10':.70,'mrr':.75,'ndcgAt10':.75}.items():
        if metrics[key]<threshold:failures.append(key)
    if metrics['unauthorizedResultCount'] or evidence.permissionLeaks:failures.append('permissionLeakage')
    latencies={}
    for stage,limit in {'retrieval':1.5,'firstAnswer':3,'searchTotal':8,'singleAnalysis':15}.items():
        samples=evidence.latencySeconds.get(stage)
        if not samples:failures.append(stage+':missing');continue
        latencies[stage]=p95(samples)
        if latencies[stage]>limit:failures.append(stage+':p95')
    fresh=sum(x<=60 for x in evidence.indexDelaySeconds)/len(evidence.indexDelaySeconds)
    success=evidence.toolSucceeded/evidence.toolAttempts
    if fresh<.99:failures.append('indexFreshness')
    if success<.99:failures.append('toolSuccess')
    return {'passed':not failures,'failedChecks':failures,'retrieval':metrics,'p95Seconds':latencies,
            'indexFreshnessRate':fresh,'toolSuccessRate':success,
            'datasetVersion':evidence.datasetVersion,'codeVersion':evidence.codeVersion,
            'evidenceSource':'operator-supplied measured data; provenance requires separate audit'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('evidence',type=Path)
    args=parser.parse_args()
    evidence=AcceptanceEvidence.model_validate_json(args.evidence.read_text(encoding='utf-8'))
    result=assess(evidence)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    if not result['passed']:raise SystemExit(1)


if __name__=='__main__':main()
