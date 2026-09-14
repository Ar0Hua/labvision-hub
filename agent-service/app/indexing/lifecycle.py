"""Preview or switch a Qdrant alias without deleting either physical collection.

Alias operation schema: https://qdrant.tech/documentation/manage-data/collections/
Operators must serialize switches and keep the previous collection for rollback.
"""
import argparse
import json
import re
from app.config import Settings
from app.indexing.qdrant_schema import QdrantSchemaManager


def switch(manager, alias, expected, target, min_points, apply=False):
    for value in (alias, expected, target):
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', value):
            raise ValueError('invalid collection or alias name')
    if len({alias, expected, target}) != 3 or min_points < 1:
        raise ValueError('alias and physical collections must be distinct; min-points must be positive')
    client, headers = manager._client, manager._headers()
    aliases = client.get('/aliases', headers=headers)
    aliases.raise_for_status()
    current = {a['alias_name']:a['collection_name'] for a in aliases.json()['result']['aliases']}
    if current.get(alias) != expected:
        raise ValueError('alias target changed or alias has not been initialized')
    response = client.get('/collections/'+target, headers=headers)
    response.raise_for_status()
    body = response.json()
    manager._verify_existing(body)
    result = body['result']
    if result.get('status') != 'green' or result.get('points_count',0) < min_points:
        raise ValueError('target not ready or does not meet expected point count')
    proposal = {'alias':alias,'previous':expected,'target':target,'points':result['points_count'],'applied':False}
    if apply:
        # All alias changes are submitted as one atomic operation, never a collection delete.
        response = client.post('/collections/aliases', headers=headers, json={'actions':[
            {'delete_alias':{'alias_name':alias}},
            {'create_alias':{'alias_name':alias,'collection_name':target}}]})
        response.raise_for_status()
        proposal['applied'] = True
    return proposal


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--alias',required=True)
    parser.add_argument('--expected-current',required=True)
    parser.add_argument('--target',required=True)
    parser.add_argument('--min-points',type=int,required=True)
    parser.add_argument('--apply',action='store_true')
    parser.add_argument('--acceptance-approved',action='store_true',help='Operator confirms target relevance/security acceptance and serialized switch')
    args=parser.parse_args()
    if args.apply and not args.acceptance_approved:
        parser.error('--apply requires explicit target acceptance approval')
    manager=QdrantSchemaManager(Settings.from_env())
    try:
        print(json.dumps(switch(manager,args.alias,args.expected_current,args.target,args.min_points,args.apply)))
    finally:
        manager.close()


if __name__=='__main__':main()
