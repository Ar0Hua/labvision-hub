"""Bounded read-only retrieval/analysis loop. Models cannot add tools or relax filters."""
import json
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from app.analysis.group_analysis import PictureGroupAnalyzer
from app.retrieval.keyword_executor import ExecutionResult
from app.runtime.scope import matches_scope, validate_scope


@dataclass
class CompositeResult:
    result: ExecutionResult
    pictures: list
    rounds: int


def group_values(picture, dimension):
    if dimension == 'space':
        return [picture.spaceId or '公共图库']
    if dimension == 'tags':
        try:
            tags = json.loads(picture.tags or '[]')
            return [str(t) for t in tags if isinstance(t, str) and t] if isinstance(tags, list) else []
        except (ValueError, TypeError):
            return []
    if dimension == 'date':
        try:
            raw = picture.createdAt
            value = (datetime.fromtimestamp(raw / 1000, timezone.utc) if isinstance(raw, int)
                     else datetime.fromisoformat(raw.replace('Z', '+00:00')))
            zone = timezone(timedelta(hours=8))
            return [(value if value.tzinfo else value.replace(tzinfo=zone)).astimezone(zone).date().isoformat()]
        except (AttributeError, ValueError, OverflowError, OSError):
            return []
    value = {'category': picture.category, 'uploader': picture.uploaderId}.get(dimension)
    return [str(value)] if value else []


class CompositeWorkflow:
    MAX_ROUNDS = 3  # initial retrieval plus at most two supplemental calls

    def execute(self, context, plan, retrieve, supplement, authorize, check_active, event):
        validate_scope(context, context.searchScope)
        def in_scope(p):
            bound = (p.spaceId is None or p.spaceId in context.allowedSpaceIds) if context.allSpaces else p.spaceId == context.spaceId
            return bound and matches_scope(p, context.searchScope)
        candidates, seen, fingerprints = {}, set(), set()
        intent = None
        stop = '补查次数已达上限'
        pictures = []
        for round_index in range(self.MAX_ROUNDS):
            check_active()
            event('RETRIEVE' if round_index == 0 else 'SUPPLEMENT', {'round': round_index + 1})
            if round_index == 0:
                result = retrieve()
                intent = result.intent_state
                if intent:
                    # The retrieval graph can inherit a narrower scope from the previous turn.
                    context.searchScope = intent.get('searchScope', context.searchScope)
                    validate_scope(context, context.searchScope)
            else:
                if not intent:
                    stop = '没有可安全复用的检索约束，未自动放宽条件'
                    break
                frozen = dict(intent)
                frozen.pop('searchScope', None)
                exclusions = list(dict.fromkeys([*frozen.get('excludePictureIds', []), *sorted(seen)]))
                if len(exclusions) > 20:
                    stop = '候选预算已达上限'
                    break
                frozen.update(excludePictureIds=exclusions, limit=20)
                result = supplement(frozen)
            check_active()
            ids = list(dict.fromkeys(c['pictureId'] for c in result.citations if c.get('pictureId')))[:20]
            fingerprint = tuple(sorted(ids))
            if fingerprint in fingerprints:
                stop = '补查未产生新结果，已停止重复调用'
                break
            fingerprints.add(fingerprint)
            seen.update(ids)
            event('FILTER', {'round': round_index + 1, 'retrieved': len(ids)})
            # Never trust model IDs or stale checkpoint metadata, nor an over-returning broker.
            for p in authorize(ids) if ids else []:
                if p.pictureId in ids and in_scope(p):
                    candidates[p.pictureId] = p
            # Recheck the accumulated set before every analysis; revoke removed resources.
            current = {}
            keys = list(candidates)
            for offset in range(0, len(keys), 20):
                check_active()
                batch = keys[offset:offset + 20]
                current.update({p.pictureId: p for p in authorize(batch)
                                if p.pictureId in batch and in_scope(p)})
            candidates = {key: current[key] for key in candidates if key in current}
            hashes, pictures = set(), []
            for p in candidates.values():
                digest = p.features.contentHash if p.features else None
                if digest and digest in hashes:
                    continue
                if digest:
                    hashes.add(digest)
                pictures.append(p)
                if len(pictures) == plan.targetCount:
                    break
            event('GROUP_ANALYSIS', {'count': len(pictures), 'groupBy': plan.groupBy})
            # Real deterministic analysis, not an LLM claim of having called a tool.
            group = PictureGroupAnalyzer.analyze(pictures) if len(pictures) >= 2 else None
            missing = sum(not group_values(p, plan.groupBy) for p in pictures)
            sufficient = len(pictures) >= plan.targetCount and missing == 0
            event('EVIDENCE_CHECK', {'count': len(pictures), 'target': plan.targetCount,
                                    'missingGroupMetadata': missing, 'sufficient': sufficient})
            if sufficient:
                stop = '数量及分组元数据满足要求'
                break
            if not ids:
                stop = '当前约束下未检索到更多图片'
                break
        # Final evidence is re-authorized even when the last attempt exhausted its budget.
        check_active()
        ids = [p.pictureId for p in pictures]
        live = {p.pictureId: p for p in authorize(ids) if p.pictureId in ids
                and in_scope(p)} if ids else {}
        pictures = [live[i] for i in ids if i in live]
        group = PictureGroupAnalyzer.analyze(pictures) if len(pictures) >= 2 else None
        if len(pictures) != len(ids):
            stop = '最终权限复核移除了已不可访问的图片'
        lines = ['## 检索与分组分析', f'目标 {plan.targetCount} 张，当前可用 {len(pictures)} 张。',
                 f'检索结束原因：{stop}。所有补查保留原检索条件和权限范围。']
        if group:
            lines.extend(['', group.answer, '', '### 本次指定分组'])
            groups = {}
            for index, p in enumerate(pictures, 1):
                for value in group_values(p, plan.groupBy) or ['未知（元数据缺失）']:
                    groups.setdefault(value, []).append(f'[图{index}]（图片 ID: {p.pictureId}）')
            for name, refs in groups.items():
                lines.append(f'- {name}：' + '、'.join(refs))
        else:
            lines.append('不足两张可用图片，无法完成图片组对比；请调整条件后重试。')
        if len(pictures) < plan.targetCount or any(not group_values(p, plan.groupBy) for p in pictures):
            lines.append('证据不完整：数量不足或分组字段缺失；以下仅为现有证据的部分成果。')
        lines.append('核验范围为当前权限、去重、样本数量和分组字段；不代表视觉判断或实验结论已被证明。')
        citations = [{'pictureId':p.pictureId, 'name':p.name, 'category':p.category} for p in pictures]
        return CompositeResult(ExecutionResult('\n\n'.join(lines), citations, len(pictures), intent),
                               pictures, len(fingerprints))
