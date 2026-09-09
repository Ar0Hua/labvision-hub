from collections import Counter
from dataclasses import dataclass
import json

from app.runtime.java_client import PictureCandidate


@dataclass(frozen=True)
class GroupAnalysisResult:
    answer: str
    citations: list[dict[str, str | None]]
    picture_count: int


class PictureGroupAnalyzer:
    TRIGGERS = ("对比", "比较", "共同点", "差异", "分组", "归类", "异常项", "代表图")

    @classmethod
    def matches(cls, query: str, picture_ids: list[str]) -> bool:
        normalized = "".join(query.split())
        return len(dict.fromkeys(picture_ids)) >= 2 and any(
            trigger in normalized for trigger in cls.TRIGGERS)

    @classmethod
    def analyze(cls, pictures: list[PictureCandidate]) -> GroupAnalysisResult:
        unique = {picture.pictureId: picture for picture in pictures}
        values = list(unique.values())
        if len(values) < 2 or len(values) > 20:
            raise ValueError("group analysis requires 2 to 20 authorized pictures")

        formats = Counter((picture.format or "未知格式").lower() for picture in values)
        categories = Counter(picture.category or "未分类" for picture in values)
        orientations = Counter(cls._orientation(picture) for picture in values)
        known_sizes = [picture.size for picture in values if picture.size is not None]
        known_widths = [picture.width for picture in values if picture.width is not None]
        known_heights = [picture.height for picture in values if picture.height is not None]
        representative = max(values, key=cls._representative_key)

        lines = [
            f"已对当前权限范围内的 {len(values)} 张图片完成确定性元数据对比：",
            "- 格式分布：" + cls._counts(formats, "张"),
            "- 分类分布：" + cls._counts(categories, "张"),
            "- 画面方向：" + cls._counts(orientations, "张"),
        ]
        if known_widths and known_heights:
            lines.append(
                f"- 分辨率范围：宽 {min(known_widths)}～{max(known_widths)} px，"
                f"高 {min(known_heights)}～{max(known_heights)} px"
                f"（{len(known_widths)}/{len(values)} 张有尺寸数据）")
        if known_sizes:
            lines.append(
                f"- 文件大小范围：{cls._size(min(known_sizes))}～{cls._size(max(known_sizes))}"
                f"（{len(known_sizes)}/{len(values)} 张有大小数据）")
        common_tags = cls._common_tags(values)
        lines.append("- 共同标签：" + ("、".join(common_tags) if common_tags else "无或数据不足"))
        lines.append(
            f"- 元数据代表项：{representative.name or '未命名图片'}"
            f" [图片 ID: {representative.pictureId}]；依据为元数据完整度和可用分辨率，"
            "不代表视觉质量或实验价值。")
        lines.append(
            "以上为数据库元数据事实；视觉内容差异、相似度矩阵、重复组和异常项需由后续"
            "视觉/向量分析提供证据，当前结果不作推断。")
        citations = [{
            "pictureId": picture.pictureId,
            "name": picture.name,
            "category": picture.category,
        } for picture in values]
        return GroupAnalysisResult("\n".join(lines), citations, len(values))

    @staticmethod
    def _orientation(picture: PictureCandidate) -> str:
        if not picture.width or not picture.height:
            return "未知"
        if picture.width == picture.height:
            return "方形"
        return "横向" if picture.width > picture.height else "纵向"

    @staticmethod
    def _counts(values: Counter, unit: str) -> str:
        return "、".join(
            f"{name} {count} {unit}"
            for name, count in sorted(values.items(), key=lambda item: (-item[1], item[0])))

    @staticmethod
    def _tags(picture: PictureCandidate) -> set[str]:
        if not picture.tags:
            return set()
        try:
            values = json.loads(picture.tags)
        except (TypeError, ValueError):
            return set()
        if not isinstance(values, list):
            return set()
        return {str(value).strip() for value in values if isinstance(value, str) and value.strip()}

    @classmethod
    def _common_tags(cls, pictures: list[PictureCandidate]) -> list[str]:
        tag_sets = [cls._tags(picture) for picture in pictures]
        if not tag_sets or any(not tags for tags in tag_sets):
            return []
        return sorted(set.intersection(*tag_sets))[:10]

    @classmethod
    def _representative_key(cls, picture: PictureCandidate) -> tuple[int, int, int]:
        completeness = sum(value is not None and value != "" for value in (
            picture.name, picture.introduction, picture.category, picture.tags,
            picture.width, picture.height, picture.size, picture.format,
        ))
        pixels = (picture.width or 0) * (picture.height or 0)
        return completeness, pixels, -int(picture.pictureId)

    @staticmethod
    def _size(value: int) -> str:
        units = ("B", "KB", "MB", "GB", "TB")
        amount = float(value)
        unit = units[0]
        for unit in units:
            if amount < 1024 or unit == units[-1]:
                break
            amount /= 1024
        return f"{amount:.2f} {unit}"
