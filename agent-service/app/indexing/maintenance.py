"""Bounded, resumable outbox backfill/reconciliation. Never edits pictures or drops collections."""
import argparse
import json
import os
import time
import uuid
from pathlib import Path
from urllib.parse import quote
from app.config import Settings
from app.indexing.pipeline import PictureIndexWorker


def needs_repair(row, point, version):
    visible = row.get('isDelete') == 0 and (row.get('spaceId') is not None or row.get('reviewStatus') == 1)
    if not visible:
        return point is not None
    if point is None or row.get('indexStatus') != 'READY' or row.get('embeddingVersion') != version:
        return True
    payload = point.get('payload', {})
    return (payload.get('sourceUpdatedAtEpoch') != row.get('sourceUpdatedAtEpoch')
            or payload.get('scopeKey') != ('public' if row.get('spaceId') is None else 'space:'+str(row['spaceId']))
            or payload.get('reviewStatus') != row.get('reviewStatus')
            or payload.get('isDelete') != row.get('isDelete'))


def run_page(worker, state, mode, limit):
    rows = worker._java_call('GET', '/agent/internal/index/jobs/maintenance/scan',
                            params={'after':state['after'],'limit':limit})
    if not isinstance(rows,list) or len(rows)>limit:
        raise ValueError('invalid maintenance page')
    ids = [int(row['pictureId']) for row in rows]
    if ids != sorted(set(ids)) or any(i<=state['after'] or i>9223372036854775807 for i in ids):
        raise ValueError('invalid maintenance cursor')
    if not rows:
        return dict(state, complete=True), 0
    if mode == 'backfill':
        repair = [str(i) for i in ids]
    else:
        response = worker._qdrant.post('/collections/'+quote(worker._settings.qdrant_collection,safe='')+'/points',
            headers=worker._qdrant_headers(), json={'ids':ids,'with_payload':True,'with_vector':False})
        response.raise_for_status()
        points = {str(p['id']):p for p in response.json()['result']}
        repair = [str(r['pictureId']) for r in rows
                  if needs_repair(r,points.get(str(r['pictureId'])),worker._settings.feature_version)]
    if repair:
        worker._java_call('POST','/agent/internal/index/jobs/maintenance/enqueue',
                         params={'runId':state['runId']},json=repair)
    # Advance only after enqueue acknowledgement. Repeating a page has the same dedupe key.
    return dict(state,after=ids[-1],complete=len(rows)<limit),len(repair)


def save_state(path, state):
    temporary = path.with_name(path.name+'.tmp')
    with temporary.open('w',encoding='utf-8') as stream:
        json.dump(state,stream); stream.flush(); os.fsync(stream.fileno())
    os.replace(temporary,path)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=['backfill','reconcile'],default='reconcile')
    parser.add_argument('--state',type=Path,required=True,help='Local cursor file; reuse to resume, new file for a new sweep')
    parser.add_argument('--limit',type=int,default=50)
    parser.add_argument('--pause-seconds',type=float,default=1)
    parser.add_argument('--max-pages',type=int,default=10)
    args=parser.parse_args()
    if not 1<=args.limit<=100 or not 1<=args.max_pages<=10000 or not .1<=args.pause_seconds<=60:
        parser.error('invalid bounds')
    settings=Settings.from_env()
    binding={'mode':args.mode,'collection':settings.qdrant_collection,'featureVersion':settings.feature_version,
             'java':settings.java_base_url,'qdrant':settings.qdrant_url}
    state=json.loads(args.state.read_text(encoding='utf-8')) if args.state.exists() else dict(binding,after=0,runId=uuid.uuid4().hex,complete=False)
    if any(state.get(k)!=v for k,v in binding.items()):
        parser.error('cursor belongs to a different maintenance target')
    worker=PictureIndexWorker(settings)
    try:
        for _ in range(args.max_pages):
            if state['complete']: break
            state,count=run_page(worker,state,args.mode,args.limit)
            save_state(args.state,state)
            print(json.dumps({'after':state['after'],'queued':count,'complete':state['complete']}),flush=True)
            if not state['complete']: time.sleep(args.pause_seconds)
    finally:
        worker.close()


if __name__=='__main__': main()
