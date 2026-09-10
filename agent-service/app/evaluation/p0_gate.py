"""Versioned in-memory contract golden set. NOT a real-model relevance benchmark."""
import argparse
import json
from pathlib import Path
from types import SimpleNamespace
from pydantic import BaseModel, ConfigDict, Field
from langgraph.checkpoint.memory import InMemorySaver
from app.graph.workflow import LangGraphWorkflow
from app.retrieval.intent import SearchIntent
from app.retrieval.keyword_executor import KeywordSearchExecutor
from app.runtime.java_client import TaskContext, PictureCandidate


class ContractCase(BaseModel):
    model_config = ConfigDict(extra='forbid')
    queryId: str
    intent: SearchIntent
    allowed: list[str]
    expected: list[str]
    pictures: list[PictureCandidate] = Field(max_length=20)


def run_cases(path: Path):
    cases = [ContractCase.model_validate(row) for row in json.loads(path.read_text(encoding='utf-8'))]
    if not cases or len({c.queryId for c in cases}) != len(cases):
        raise ValueError('golden cases must have unique IDs and not be empty')
    failures=[]
    for case in cases:
        parser=SimpleNamespace(parse=lambda *_, case=case:case.intent.model_copy(deep=True))
        workflow=LangGraphWorkflow(KeywordSearchExecutor(parser),InMemorySaver())
        context=TaskContext(taskId=case.queryId,conversationId='contract',userId='7',spaceId='9',
                            query=case.intent.searchText,status='RUNNING')
        result=workflow.execute(context,lambda *_,case=case:case.pictures,
            lambda ids,case=case:[p for p in case.pictures if p.pictureId in ids and p.pictureId in case.allowed],lambda:None)
        ids=[c['pictureId'] for c in result.citations]
        if ids != case.expected or any(i not in case.allowed for i in ids):
            failures.append(case.queryId)
    return {'suite':'p0-contract-v1','cases':len(cases),'passed':len(cases)-len(failures),
            'failedCaseIds':failures,'realModelBenchmark':False}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('golden',type=Path)
    result=run_cases(parser.parse_args().golden)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    if result['failedCaseIds']:
        raise SystemExit(1)

if __name__=='__main__':
    main()
