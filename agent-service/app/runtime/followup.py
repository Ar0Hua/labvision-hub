"""Resolve explicit ordinal references before routing. Never shift an unavailable index."""
import re
from dataclasses import dataclass
from app.runtime.planner import TaskPlan
from app.runtime.scope import validate_scope, matches_scope


class FollowupClarification(ValueError):
    pass


@dataclass
class ResultReference:
    count: int
    ordinal: bool
    group_by: str
    visual: bool


def parse_reference(query):
    if not any(word in query for word in ('刚才', '上一轮', '上轮', '上次', '刚刚')):
        return None
    if not any(word in query for word in ('分析', '解释', '描述', '对比', '比较', '分组')):
        return None
    if any(word in query for word in ('删除', '修改', '移动', '授权', '搜索', '检索', '查找')):
        raise FollowupClarification('请将历史图片分析与检索、修改等其他操作分开提问。')
    matches = list(re.finditer(r'(前|第)\s*([0-9一二三四五六七八九十两]+)\s*张', query))
    if len(matches) != 1:
        raise FollowupClarification('请明确引用上一轮的第几张或前几张，例如“分析上一轮第2张”。')
    value = matches[0][2]
    digits = {'一':1,'二':2,'两':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9}
    if value.isascii() and value.isdigit():
        number = int(value)
    elif value in digits:
        number = digits[value]
    elif value == '十':
        number = 10
    elif re.fullmatch(r'[一二]?十[一二三四五六七八九]?', value):
        left, right = value.split('十')
        number = digits.get(left,1)*10 + digits.get(right,0)
    else:
        raise FollowupClarification('无法识别图片序号，请使用1到20之间的数字。')
    if not 1 <= number <= 20:
        raise FollowupClarification('一次最多引用上一轮的20张图片，请使用1到20之间的序号或数量。')
    dimensions = [value for words,value in [(('项目','空间'),'space'),(('分类',),'category'),
                  (('标签',),'tags'),(('上传人',),'uploader'),(('日期','时间'),'date')]
                  if any(word in query for word in words)]
    if len(set(dimensions)) > 1:
        raise FollowupClarification('请一次指定一个分组维度：项目空间、分类、标签、上传人或日期。')
    return ResultReference(number, matches[0][1]=='第', dimensions[0] if dimensions else 'category',
                           any(w in query for w in ('分析','解释','描述','对比','比较')))


def resolve_reference(context, reference, snapshot, authorize):
    if not isinstance(snapshot, dict) or not snapshot.get('pictureIds'):
        raise FollowupClarification('当前会话没有可引用的上一轮图片结果，或历史缓存已过期。请先检索图片。')
    ids = snapshot['pictureIds']
    if not isinstance(ids,list) or len(ids)>20 or any(not isinstance(i,str) or not i.isdigit() for i in ids):
        raise FollowupClarification('历史结果记录不可用，请重新检索。')
    if reference.count > len(ids):
        raise FollowupClarification(f'上一轮只有{len(ids)}张图片，无法引用第{reference.count}张或前{reference.count}张。')
    scope = snapshot.get('scope')
    validate_scope(context, scope)
    if context.searchScope is not None and context.searchScope != scope:
        raise FollowupClarification('检索范围已变更，请在当前范围重新检索后再引用图片。')
    selected = [ids[reference.count-1]] if reference.ordinal else ids[:reference.count]
    # Resolve positions before authorization. Missing second picture never becomes the third.
    live = {p.pictureId:p for p in authorize(selected)
            if p.pictureId in selected and matches_scope(p,scope)
            and ((p.spaceId is None or p.spaceId in context.allowedSpaceIds) if context.allSpaces else p.spaceId==context.spaceId)}
    if any(i not in live for i in selected):
        raise FollowupClarification('引用的图片已删除、不可访问或不在当前范围，未使用其他图片替代。请重新检索。')
    context.examplePictureIds = selected
    context.searchScope = scope
    return TaskPlan(task='picture_analysis' if len(selected)==1 else 'picture_group_analysis',
                    groupBy=reference.group_by, visualAnalysis=reference.visual)
