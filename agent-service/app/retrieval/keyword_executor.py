from dataclasses import dataclass
import json
from typing import Callable

from app.runtime.java_client import PictureCandidate, TaskContext
from app.retrieval.intent import IntentParser


SearchPictures = Callable[[str, str | None, list[str], int], list[PictureCandidate]]


@dataclass(frozen=True)
class ExecutionResult:
    answer: str
    citations: list[dict[str, str | None]]
    candidate_count: int


class KeywordSearchExecutor:
    """Baseline real executor backed by Java's permission-scoped MySQL search."""

    def __init__(self, parser: IntentParser) -> None:
        self._parser = parser

    def execute(self, context: TaskContext, search: SearchPictures) -> ExecutionResult:
        intent = self._parser.parse(context.query)
        candidates = search(intent.searchText, intent.category, intent.tags, intent.limit)
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
