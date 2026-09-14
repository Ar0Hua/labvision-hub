"""Run one resumable reconciliation sweep per UTC day; no model calls in this process."""
import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from app.config import Settings
from app.indexing.pipeline import PictureIndexWorker
from app.indexing.maintenance import run_page, save_state
import hashlib
import uuid


def sweep_page(worker, directory, day):
    settings=worker._settings
    binding={'collection':settings.qdrant_collection,'featureVersion':settings.feature_version,
             'java':settings.java_base_url,'qdrant':settings.qdrant_url}
    digest=hashlib.sha256(json.dumps(binding,sort_keys=True).encode()).hexdigest()[:20]
    path=directory / (day+'-'+digest+'.json')
    state=json.loads(path.read_text(encoding='utf-8')) if path.exists() else dict(binding,after=0,runId=uuid.uuid4().hex,complete=False)
    if any(state.get(k)!=v for k,v in binding.items()):raise ValueError('maintenance target mismatch')
    if state['complete']:return {'complete':True,'queued':0}
    state,count=run_page(worker,state,'reconcile',50)
    save_state(path,state)
    return {'complete':state['complete'],'queued':count}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state-dir',required=True,type=Path)
    parser.add_argument('--once',action='store_true',help='Process one bounded page and exit')
    args=parser.parse_args()
    args.state_dir.mkdir(parents=True,exist_ok=True)
    worker=PictureIndexWorker(Settings.from_env())
    # OS-level nonblocking lock is automatically released after process termination.
    with (args.state_dir/'scheduler.lock').open('a+b') as lock:
        lock.seek(0); lock.write(b'0'); lock.flush(); lock.seek(0)
        import os
        if os.name=='nt':
            import msvcrt
            msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        else:
            import fcntl
            fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        try:
            while True:
                try:
                    result=sweep_page(worker,args.state_dir,datetime.now(timezone.utc).strftime('%Y-%m-%d'))
                    print(json.dumps(result),flush=True)
                except Exception as error:
                    if args.once:raise
                    print(json.dumps({'error':type(error).__name__}),flush=True)
                    time.sleep(30)
                    continue
                if args.once:break
                time.sleep(60 if result['complete'] else 1)
        finally:
            worker.close()


if __name__=='__main__':main()
