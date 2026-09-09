from datetime import datetime
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SpaceScope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["public", "space"]
    spaceId: str | None = None

    @model_validator(mode="after")
    def validate_scope(self) -> Self:
        if self.type == "public" and self.spaceId is not None:
            raise ValueError("public scope must not contain a space ID")
        if self.type == "space":
            if (self.spaceId is None or not self.spaceId.isdigit()
                    or int(self.spaceId) < 1
                    or int(self.spaceId) > 9_223_372_036_854_775_807):
                raise ValueError("space scope requires a valid space ID")
        return self


class SpaceUsage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    usedSize: int = Field(ge=0)
    maxSize: int | None = Field(default=None, ge=0)
    sizeUsageRatio: float | None = Field(default=None, ge=0)
    usedCount: int = Field(ge=0)
    maxCount: int | None = Field(default=None, ge=0)
    countUsageRatio: float | None = Field(default=None, ge=0)


class CategoryStat(BaseModel):
    model_config = ConfigDict(extra="forbid")
    category: str | None = None
    count: int = Field(ge=0)
    totalSize: int = Field(ge=0)


class TagStat(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tag: str
    count: int = Field(ge=0)


class SizeStat(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sizeRange: str
    count: int = Field(ge=0)


class TrendStat(BaseModel):
    model_config = ConfigDict(extra="forbid")
    period: str
    count: int = Field(ge=0)


class Governance(BaseModel):
    model_config = ConfigDict(extra="forbid")
    totalCount: int = Field(default=0, ge=0)
    untaggedCount: int = Field(default=0, ge=0)
    staleCount: int = Field(default=0, ge=0)
    unknownResolutionCount: int = Field(default=0, ge=0)
    underOneMegapixelCount: int = Field(default=0, ge=0)
    oneToFourMegapixelCount: int = Field(default=0, ge=0)
    overFourMegapixelCount: int = Field(default=0, ge=0)
    indexedCount: int = Field(default=0, ge=0)
    qualityIssueCount: int = Field(default=0, ge=0)
    duplicateExcessCount: int = Field(default=0, ge=0)


class WindowTotals(BaseModel):
    model_config = ConfigDict(extra="forbid")
    count: int = Field(ge=0)
    totalSize: int = Field(ge=0)


class UploaderStat(BaseModel):
    model_config = ConfigDict(extra="forbid")
    uploaderId: str | None = None
    count: int = Field(ge=0)


class StatisticsWindow(BaseModel):
    model_config = ConfigDict(extra="forbid")
    startDate: str | None = None
    endDate: str | None = None
    uploaderId: str | None = None
    totals: WindowTotals
    categories: list[CategoryStat] = Field(max_length=20)
    uploaders: list[UploaderStat] = Field(max_length=20)
    trend: list[TrendStat] = Field(max_length=24)


class SpaceStatistics(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scope: SpaceScope
    capturedAt: datetime
    window: StatisticsWindow | None = None
    governance: Governance | None = None
    usage: SpaceUsage
    categoryDistribution: list[CategoryStat] = Field(max_length=20)
    tagDistribution: list[TagStat] = Field(max_length=20)
    sizeDistribution: list[SizeStat] = Field(max_length=20)
    monthlyUploadTrend: list[TrendStat] = Field(max_length=24)
    distributionLimit: int = Field(ge=1, le=20)
    trendLimit: int = Field(ge=1, le=24)

    @model_validator(mode="after")
    def validate_timestamp(self) -> Self:
        if self.capturedAt.tzinfo is None:
            raise ValueError("statistics timestamp must include a timezone")
        return self


class SpaceStatisticsComposer:
    TRIGGERS = (
        "上传人统计", "上传行为",
        "无标签", "未打标签", "重复率", "低质量率", "分辨率分布", "未维护",
        "空间统计", "空间容量", "容量使用", "使用率", "图片数量", "资产数量",
        "分类分布", "标签分布", "大小分布", "上传趋势", "上传数量",
        "多少图片", "多少张图", "多少资产", "用了多少容量", "占用多少容量",
    )

    @classmethod
    def matches(cls, query: str) -> bool:
        normalized = "".join(query.split())
        return any(trigger in normalized for trigger in cls.TRIGGERS)

    @classmethod
    def compose(cls, summary: SpaceStatistics) -> str:
        scope = ("公共图库" if summary.scope.type == "public"
                 else f"空间 {summary.scope.spaceId}")
        usage = summary.usage
        lines = [
            f"{scope} 的确定性统计（采集时间：{summary.capturedAt.isoformat()}）：",
            f"- 图片数量：{usage.usedCount} 张",
            f"- 已用容量：{cls._size(usage.usedSize)}",
        ]
        if usage.maxCount is not None:
            ratio = f"，使用率 {usage.countUsageRatio:.2f}%" if usage.countUsageRatio is not None else ""
            lines.append(f"- 图片数量上限：{usage.maxCount} 张{ratio}")
        if usage.maxSize is not None:
            ratio = f"，使用率 {usage.sizeUsageRatio:.2f}%" if usage.sizeUsageRatio is not None else ""
            lines.append(f"- 容量上限：{cls._size(usage.maxSize)}{ratio}")
        if summary.governance:
            g = summary.governance
            lines.extend([
                f"- 无标签：{g.untaggedCount}/{g.totalCount}；180 天未维护：{g.staleCount}/{g.totalCount}。",
                f"- 分辨率：低于 100 万像素 {g.underOneMegapixelCount}；100～400 万 {g.oneToFourMegapixelCount}；"
                f"至少 400 万 {g.overFourMegapixelCount}；未知 {g.unknownResolutionCount}。",
                f"- 当前版本索引覆盖：{g.indexedCount}/{g.totalCount}。",
            ])
            if g.indexedCount:
                lines.append(f"- 已索引图片质量问题候选：{g.qualityIssueCount}/{g.indexedCount}；"
                             f"相同索引图像冗余项：{g.duplicateExcessCount}/{g.indexedCount}。")
            lines.append("- 质量阈值为亮度低于 50/高于 210 或模糊度低于 45；"
                         "哈希基于索引图像，不能等同于原始文件重复率。")
        if summary.categoryDistribution:
            values = "、".join(
                f"{item.category or '未分类'} {item.count} 张"
                for item in summary.categoryDistribution[:5])
            lines.append("- 主要分类：" + values)
        if summary.tagDistribution:
            values = "、".join(
                f"{item.tag} {item.count} 次" for item in summary.tagDistribution[:5])
            lines.append("- 常用标签：" + values)
        if summary.sizeDistribution:
            values = "、".join(
                f"{item.sizeRange} {item.count} 张" for item in summary.sizeDistribution)
            lines.append("- 文件大小分布：" + values)
        if summary.monthlyUploadTrend:
            values = "、".join(
                f"{item.period}：{item.count} 张" for item in summary.monthlyUploadTrend[-6:])
            lines.append("- 最近上传趋势：" + values)
        if summary.window:
            w = summary.window
            filtered = [
                f"筛选窗口：{w.startDate or '不限起始'} 至 {w.endDate or '不限结束'}（UTC+8，包含结束日）；"
                f"上传人 ID：{w.uploaderId or '全部'}。",
                f"- 窗口图片数量：{w.totals.count}；文件总大小：{cls._size(w.totals.totalSize)}。",
                "- 窗口分类：" + "、".join(f"{c.category or '未分类'} {c.count}" for c in w.categories),
                "- 窗口上传人：" + "、".join(f"{u.uploaderId or '未知'} {u.count}" for u in w.uploaders),
                "- 窗口月度趋势：" + "、".join(f"{t.period} {t.count}" for t in w.trend),
                "", "以下是当前全空间快照，不受上述窗口筛选限制：",
            ]
            lines = filtered + lines
        lines.append("以上数值来自当前权限范围内的数据库统计，不是模型估算。")
        return "\n".join(lines)

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
