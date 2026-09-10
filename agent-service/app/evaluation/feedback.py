"""Prepare human-review drafts from authorized JSON reports; never auto-train or promote labels."""
import argparse
import json
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, Field


class Feedback(BaseModel):
    pictureId: str = Field(pattern=r'^[1-9][0-9]{0,18}$')
    label: Literal['relevant','irrelevant','duplicate','permission_issue']


def prepare(report):
    if report.get('version')!='labvision-report-v1':
        raise ValueError('unsupported report version')
    citations=report.get('citations',[])
    if not isinstance(citations,list) or len(citations)>20:
        raise ValueError('invalid report citations')
    ids=[item['pictureId'] for item in citations]
    if len(set(ids))!=len(ids):
        raise ValueError('duplicate citations')
    feedback=[Feedback.model_validate(row) for row in report.get('feedback',[])]
    if len(feedback)>20 or len({f.pictureId for f in feedback})!=len(feedback):
        raise ValueError('invalid feedback count')
    if any(f.pictureId not in ids for f in feedback):
        raise ValueError('feedback is not supported by report citations')
    return {'version':'feedback-review-v1','requiresHumanReview':True,
            'rankedPictureIds':ids,
            'suggestedRelevantPictureIds':[f.pictureId for f in feedback if f.label=='relevant'],
            'labels':[f.model_dump() for f in feedback],
            'warning':'权限异常报告不是已证明的越权；人工复核后才纳入独立golden set，不自动更新在线模型或权重。'}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('report',type=Path)
    draft=prepare(json.loads(parser.parse_args().report.read_text(encoding='utf-8')))
    print(json.dumps(draft,ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
