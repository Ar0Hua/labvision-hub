from collections import Counter
from dataclasses import dataclass
import json

from app.retrieval.semantic import PictureSimilarityMatrix
from app.analysis.vector_groups import summarize_vector_groups
from app.runtime.java_client import PictureCandidate


@dataclass(frozen=True)
class GroupAnalysisResult:
    answer: str
    citations: list[dict[str, str | None]]
    picture_count: int


@dataclass(frozen=True)
class GroupSimilarityResult:
    answer: str
    known_pair_count: int
    total_pair_count: int


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
            "以上为数据库元数据事实；向量与视觉证据将在可用时追加，"
            "重复组和异常项仍需后续分析，当前结果不作推断。")
        citations = [{
            "pictureId": picture.pictureId,
            "name": picture.name,
            "category": picture.category,
        } for picture in values]
        return GroupAnalysisResult("\n".join(lines), citations, len(values))

    @classmethod
    def analyze_similarity(
        cls, pictures: list[PictureCandidate], matrix: PictureSimilarityMatrix,
    ) -> GroupSimilarityResult:
        unique = {picture.pictureId: picture for picture in pictures}
        picture_ids = list(unique)
        if matrix.picture_ids != picture_ids:
            raise ValueError("similarity matrix does not match authorized picture order")
        grouping = summarize_vector_groups(matrix)
        count = len(picture_ids)
        if len(matrix.scores) != count or any(
            len(row) != count for row in matrix.scores
        ):
            raise ValueError("invalid similarity matrix dimensions")

        pairs: list[tuple[str, str, float]] = []
        related: dict[str, list[float]] = {picture_id: [] for picture_id in picture_ids}
        for left_index, left in enumerate(picture_ids):
            for right_index in range(left_index + 1, count):
                score = matrix.scores[left_index][right_index]
                if score is None:
                    continue
                right = picture_ids[right_index]
                pairs.append((left, right, score))
                related[left].append(score)
                related[right].append(score)

        total_pairs = count * (count - 1) // 2
        lines = [
            f"图像向量相似度证据（覆盖 {len(pairs)}/{total_pairs} 对，Qdrant Cosine）：",
            "| 图片 ID | " + " | ".join(picture_ids) + " |",
            "|---|" + "|".join("---:" for _ in picture_ids) + "|",
        ]
        for row_id, row in zip(picture_ids, matrix.scores):
            values = ["—" if value is None else f"{value:.3f}" for value in row]
            lines.append(f"| {row_id} | " + " | ".join(values) + " |")

        if not pairs:
            lines.append("- 当前没有足够的已索引图像向量，不能计算代表图或最高相似图片对。")
            return GroupSimilarityResult("\n".join(lines), 0, total_pairs)

        most_similar = max(
            pairs, key=lambda item: (item[2], -int(item[0]), -int(item[1]))
        )
        lines.append(
            f"- 最高相似图片对：{cls._picture_label(unique[most_similar[0]])} 与 "
            f"{cls._picture_label(unique[most_similar[1]])}，余弦相似度 "
            f"{most_similar[2]:.3f}。")

        representative_id = max(
            picture_ids,
            key=lambda picture_id: (
                len(related[picture_id]),
                sum(related[picture_id]) / len(related[picture_id])
                if related[picture_id] else -2.0,
                -int(picture_id),
            ),
        )
        representative_scores = related[representative_id]
        lines.append(
            f"- 向量中心代表项：{cls._picture_label(unique[representative_id])}；"
            f"与其余图片的已知平均相似度 "
            f"{sum(representative_scores) / len(representative_scores):.3f}"
            f"（有效关联 {len(representative_scores)}/{count - 1}）。")
        lines.append(
            "- 上述代表性仅表示当前图像向量集合中的中心程度，不代表视觉质量、"
            "实验价值或科研结论。")
        return GroupSimilarityResult("\n".join(lines) + "\n\n" + grouping, len(pairs), total_pairs)

    @staticmethod
    def _picture_label(picture: PictureCandidate) -> str:
        return f"{picture.name or '未命名图片'} [图片 ID: {picture.pictureId}]"

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
