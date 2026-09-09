"""Quality and duplicate evidence derived only from current authorized features."""
from collections import defaultdict
from app.runtime.java_client import PictureCandidate


def summarize_features(pictures: list[PictureCandidate]) -> str:
    available = [p for p in pictures if p.features is not None]
    lines = [f"质量与哈希证据（覆盖 {len(available)}/{len(pictures)} 张）：", ""]
    exact = defaultdict(list)
    for picture in available:
        f = picture.features
        facts = []
        if f.brightnessScore is not None:
            state = "偏暗" if f.brightnessScore < 50 else "偏亮" if f.brightnessScore > 210 else "常规范围"
            facts.append(f"灰度均值 {f.brightnessScore:.2f}（{state}）")
        if f.blurScore is not None:
            facts.append(f"拉普拉斯方差 {f.blurScore:.2f}" + ("（疑似模糊）" if f.blurScore < 45 else ""))
        if facts:
            lines.append(f"- [图片 ID: {picture.pictureId}]：" + "；".join(facts))
        if f.contentHash:
            exact[f.contentHash].append(picture.pictureId)
        if len(pictures) == 1:
            if f.caption:
                lines.append("- 索引视觉描述（模型观察）：" + f.caption)
            if f.ocrText:
                lines.append("- 索引可见文字（模型识别）：" + f.ocrText)
    for ids in exact.values():
        if len(ids) > 1:
            lines.append("- 索引图像字节相同：" + "、".join(f"[图片 ID: {i}]" for i in ids))
    pairs = []
    for i, left in enumerate(available):
        for right in available[i+1:]:
            a, b = left.features, right.features
            if a.contentHash and a.contentHash == b.contentHash:
                continue
            if all((a.phash, b.phash, a.dhash, b.dhash)):
                pd = (int(a.phash, 16) ^ int(b.phash, 16)).bit_count()
                dd = (int(a.dhash, 16) ^ int(b.dhash, 16)).bit_count()
                if pd <= 6 and dd <= 6:
                    pairs.append((left.pictureId, right.pictureId, pd, dd))
    for a, b, pd, dd in pairs[:20]:
        lines.append(f"- 近重复候选：[图片 ID: {a}] 与 [图片 ID: {b}]；pHash 距离 {pd}/64，dHash 距离 {dd}/64。")
    if len(pairs) > 20:
        lines.append(f"- 共 {len(pairs)} 对候选，仅展示前 20 对。")
    if not available:
        lines.append("- 尚无与当前图片版本匹配的索引特征。")
    lines.append("- 特征基于索引时使用的图像（可能为缩略图）；字节相同不能证明原始文件相同。"
                 "近重复阈值为两种哈希距离均不超过 6，质量阈值尚需真实数据校准；候选需人工复核。")
    return "\n".join(lines)
