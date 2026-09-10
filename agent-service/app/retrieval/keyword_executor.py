from dataclasses import dataclass
import json
from typing import Callable

from app.runtime.java_client import PictureCandidate, TaskContext
from app.retrieval.intent import IntentParser
from app.retrieval.fusion import reciprocal_rank_fusion
from app.retrieval.ordering import order_candidates
from app.retrieval.semantic import SemanticRetriever


SearchPictures = Callable[[str, str | None, list[str], int, dict], list[PictureCandidate]]
AuthorizePictures = Callable[[list[str]], list[PictureCandidate]]
CheckActive = Callable[[], None]


@dataclass(frozen=True)
class ExecutionResult:
    answer: str
    citations: list[dict[str, str | None]]
    candidate_count: int
    intent_state: dict | None = None


class KeywordSearchExecutor:
    """Baseline real executor backed by Java's permission-scoped MySQL search."""

    def __init__(self, parser: IntentParser, semantic: SemanticRetriever | None = None) -> None:
        self._parser = parser
        self._semantic = semantic

    def execute(
        self, context: TaskContext, search: SearchPictures, authorize: AuthorizePictures,
        check_active: CheckActive,
    ) -> ExecutionResult:
        return self.execute_with_state(context, search, authorize, check_active, None, [])

    def execute_with_state(
        self, context: TaskContext, search: SearchPictures, authorize: AuthorizePictures,
        check_active: CheckActive, previous_intent: dict | None,
        previous_result_ids: list[str],
    ) -> ExecutionResult:
        intent = self._parser.parse(context.query, previous_intent, previous_result_ids)
        if context.examplePictureIds:
            intent.examplePictureIds = context.examplePictureIds
        check_active()
        filters = {
            "formats": intent.formats,
            "category": intent.category,
            "tags": intent.tags,
            "createdAfter": intent.createdAfter.isoformat() if intent.createdAfter else None,
            "createdBefore": intent.createdBefore.isoformat() if intent.createdBefore else None,
            "minWidth": intent.minWidth,
            "minHeight": intent.minHeight,
            "maxSizeBytes": intent.maxSizeBytes,
            "uploaderId": intent.uploaderId,
            "minAspectRatio": intent.minAspectRatio,
            "maxAspectRatio": intent.maxAspectRatio,
            "sort": intent.sort,
            "excludePictureIds": intent.excludePictureIds,
        }
        excluded = set(intent.excludePictureIds)
        keyword = [
            picture for picture in search(
                intent.searchText, intent.category, intent.tags, intent.limit, filters)
            if picture.pictureId not in excluded
        ]
        check_active()
        metadata = {picture.pictureId: picture for picture in keyword}
        channels = {"keyword": [picture.pictureId for picture in keyword]}
        if self._semantic and self._semantic.enabled:
            scope_key = "public" if context.spaceId is None else "space:" + context.spaceId
            try:
                vector_ids = self._semantic.search(intent.searchText, scope_key, 20, filters)
                check_active()
                authorized = authorize(vector_ids)
                check_active()
                metadata.update({picture.pictureId: picture for picture in authorized})
                channels["vector"] = [picture.pictureId for picture in authorized]
            except Exception:
                pass
            if intent.examplePictureIds:
                try:
                    example_candidates = authorize(intent.examplePictureIds)
                    allowed_examples = {picture.pictureId for picture in example_candidates}
                    intent.examplePictureIds = [
                        picture_id for picture_id in intent.examplePictureIds
                        if picture_id in allowed_examples
                    ]
                    if not intent.examplePictureIds:
                        raise ValueError("no authorized example pictures")
                    image_ids = self._semantic.search_by_pictures(
                        intent.examplePictureIds, scope_key, 20, filters)
                    check_active()
                    image_candidates = authorize(image_ids)
                    check_active()
                    metadata.update({picture.pictureId: picture for picture in image_candidates})
                    channels["image"] = [picture.pictureId for picture in image_candidates]
                except Exception:
                    pass
        weights = {name: (1.5 if name == "image" else 1.0) for name in channels}
        ranking = reciprocal_rank_fusion(
            channels, top_k=50, weights=weights
        )
        candidates = [
            metadata[item.picture_id] for item in ranking
            if item.picture_id in metadata and item.picture_id not in excluded
        ]
        # Recheck the final fused set and attach only current Java-provided features.
        checked = []
        for offset in range(0, len(candidates), 20):
            check_active()
            checked.extend(authorize([picture.pictureId
                                      for picture in candidates[offset:offset + 20]]))
        authorized = {picture.pictureId: picture for picture in checked}
        candidates = [authorized[p.pictureId] for p in candidates if p.pictureId in authorized]
        if intent.uploaderId is not None:
            candidates = [p for p in candidates if p.uploaderId == intent.uploaderId]
        if intent.minAspectRatio is not None or intent.maxAspectRatio is not None:
            candidates = [p for p in candidates if p.width and p.height and p.width > 0 and p.height > 0
                          and (intent.minAspectRatio is None or p.width / p.height >= intent.minAspectRatio)
                          and (intent.maxAspectRatio is None or p.width / p.height <= intent.maxAspectRatio)]
        check_active()
        candidates = order_candidates(candidates, intent.sort)
        seen_hashes = set()
        visible = []
        collapsed = 0
        for picture in candidates:
            digest = picture.features.contentHash if picture.features else None
            if digest and digest in seen_hashes:
                collapsed += 1
                continue
            if digest:
                seen_hashes.add(digest)
            visible.append(picture)
        candidates = visible[:intent.limit]
        citations = [
            {
                "pictureId": picture.pictureId,
                "name": picture.name,
                "category": picture.category,
            }
            for picture in candidates
        ]
        if not candidates:
            return ExecutionResult(
                answer="当前会话可访问的图片中，没有找到与该关键词匹配的视觉资产。",
                citations=[],
                intent_state=intent.model_dump(mode="json"),
                candidate_count=0,
            )
        lines = [f"在当前会话可访问范围内找到 {len(candidates)} 项相关视觉资产："]
        if intent.sort != "relevance":
            direction = "从新到旧" if intent.sort == "newest" else "从旧到新"
            lines.append(f"排序：本次融合候选（最多 50 项）内按上传时间{direction}；"
                         "时间缺失或无效的项置后，不代表全库时间排名。")
        for index, picture in enumerate(candidates[:5], start=1):
            name = self._short(picture.name or "未命名图片", 60)
            details = []
            if picture.category:
                details.append("分类：" + self._short(picture.category, 30))
            tags = self._tags(picture.tags)
            if tags:
                details.append("标签：" + "、".join(tags[:3]))
            matched = [name for name, ids in channels.items() if picture.pictureId in ids]
            labels = {"keyword": "关键词/元数据匹配", "vector": "文本语义匹配", "image": "图像向量匹配"}
            details.append("匹配依据：" + "、".join(labels[name] for name in matched))
            suffix = "；".join(details)
            if suffix:
                suffix = "（" + suffix + "）"
            lines.append(f"{index}. {name}{suffix} [图片 ID: {picture.pictureId}]")
        if collapsed:
            lines.append(f"已折叠 {collapsed} 项索引图像字节相同的结果；不等同于原始文件相同。")
        if len(candidates) > 5:
            lines.append(f"另有 {len(candidates) - 5} 项结果，可继续缩小关键词范围。")
        return ExecutionResult("\n".join(lines), citations, len(candidates),
                               intent.model_dump(mode="json"))

    @staticmethod
    def _short(value: str, limit: int) -> str:
        cleaned = " ".join(value.split())
        return cleaned if len(cleaned) <= limit else cleaned[:limit] + "…"

    @classmethod
    def _tags(cls, value: str | None) -> list[str]:
        if not value:
            return []
        try:
            parsed = json.loads(value)
        except (TypeError, ValueError):
            return []
        if not isinstance(parsed, list):
            return []
        return [cls._short(str(tag), 20) for tag in parsed if isinstance(tag, str) and tag.strip()]
