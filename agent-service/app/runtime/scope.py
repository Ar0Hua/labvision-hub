"""Narrow retrieval inside signed conversation scope; never grant new permissions."""


def validate_scope(context, scope):
    if scope is None or scope == 'all':return
    if scope == 'public':
        if context.allSpaces or context.spaceId is None:return
    elif scope.startswith('space:'):
        value=scope[6:]
        if value == context.spaceId or context.allSpaces and value in context.allowedSpaceIds:return
    raise ValueError('requested scope is outside conversation')


def resolve_scope(context, name, spaces):
    if name == '公共图库':scope='public'
    elif name == '全部授权空间':scope='all'
    else:
        matches=[s for s in spaces if s.spaceName.strip()==name.strip() and s.spaceId]
        if len(matches)!=1:raise ValueError('space missing or ambiguous')
        scope='space:'+matches[0].spaceId
    validate_scope(context,scope)
    return scope


def matches_scope(picture, scope):
    return scope in (None,'all') or scope == ('public' if picture.spaceId is None else 'space:'+picture.spaceId)
