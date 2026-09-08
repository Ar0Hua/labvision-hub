from dataclasses import dataclass
import json
from typing import Callable

from app.runtime.java_client import PictureCandidate, TaskContext
from app.retrieval.intent import IntentParser
from app.retrieval.fusion import reciprocal_rank_fusion
from app.retrieval.semantic import SemanticRetriever


SearchPictures = Callable[[str, str | None, list[str], int, dict], list[PictureCandidate]]
AuthorizePictures = Callable[[list[str]], list[PictureCandidate]]
CheckActive = Callable[[], None]


@dataclass(frozen=True)
class ExecutionResult:
    answer: str
    citations: list[dict[str, str | None]]
    candidate_count: int


class KeywordSearchExecutor:
    """Baseline real executor backed by Java's permission-scoped MySQL search."""

    def __init__(self, parser: IntentParser, semantic: SemanticRetriever | None = None) -> None:
        self._parser = parser
        self._semantic = semantic

    def execute(
        self, context: TaskContext, search: SearchPictures, authorize: AuthorizePictures,
        check_active: CheckActive,
    ) -> ExecutionResult:
        intent = self._parser.parse(context.query)
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
            "sort": intent.sort,
        }
        keyword = search(intent.searchText, intent.category, intent.tags, intent.limit, filters)
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
            if context.examplePictureIds:
                try:
                    image_ids = self._semantic.search_by_pictures(
                        context.examplePictureIds, scope_key, 20, filters)
                    check_active()
                    image_candidates = authorize(image_ids)
                    check_active()
                    metadata.update({picture.pictureId: picture for picture in image_candidates})
                    channels["image"] = [picture.pictureId for picture in image_candidates]
                except Exception:
                    pass
        weights = {name: (1.5 if name == "image" else 1.0) for name in channels}
        ranking = reciprocal_rank_fusion(
            channels, top_k=intent.limit, weights=weights
        )
        candidates = [metadata[item.picture_id] for item in ranking if item.picture_id in metadata]
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
                candidate_count=0,
            )
        lines = [f"在当前会话可访问范围内找到 {len(candidates)} 项相关视觉资产："]
        for index, picture in enumerate(candidates[:5], start=1):
            name = self._short(picture.name or "未命名图片", 60)
            details = []
            if picture.category:
                details.append("分类：" + self._short(picture.category, 30))
            tags = self._tags(picture.tags)
            if tags:
                details.append("标签：" + "、".join(tags[:3]))
            suffix = "；".join(details)
            if suffix:
                suffix = "（" + suffix + "）"
            lines.append(f"{index}. {name}{suffix} [图片 ID: {picture.pictureId}]")
        if len(candidates) > 5:
            lines.append(f"另有 {len(candidates) - 5} 项结果，可继续缩小关键词范围。")
        return ExecutionResult("\n".join(lines), citations, len(candidates))

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
