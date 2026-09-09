"""Deterministic grouping of authorized image vectors."""
import math

from app.retrieval.semantic import PictureSimilarityMatrix


def summarize_vector_groups(matrix: PictureSimilarityMatrix) -> str:
    ids, scores = matrix.picture_ids, matrix.scores
    n = len(ids)
    if not 2 <= n <= 20 or len(set(ids)) != n:
        raise ValueError("invalid group size")
    if len(scores) != n or any(len(row) != n for row in scores):
        raise ValueError("invalid matrix dimensions")
    for i in range(n):
        for j in range(n):
            value = scores[i][j]
            if value is not None and (
                isinstance(value, bool) or not isinstance(value, (int, float))
                or not math.isfinite(value) or not -1 <= value <= 1
            ):
                raise ValueError("invalid cosine score")
            if value != scores[j][i]:
                raise ValueError("asymmetric matrix")
    groups = [[i] for i in sorted(range(n), key=lambda i: int(ids[i]))]
    while True:
        candidates = []
        for a in range(len(groups)):
            for b in range(a + 1, len(groups)):
                cross = [scores[i][j] for i in groups[a] for j in groups[b]]
                if all(v is not None and v >= .85 for v in cross):
                    candidates.append((min(cross), -a, -b))
        if not candidates:
            break
        _, a, b = max(candidates)
        a, b = -a, -b
        groups[a] = sorted(groups[a] + groups[b], key=lambda i: int(ids[i]))
        del groups[b]
    lines = [
        "向量分组与离群候选：", "",
        "- 分组要求组内每对相似度至少 0.850；离群要求至少 3 张图片、与其余图片分数全部已知且最高值低于 0.300。",
        "- 阈值尚未经过实验室数据校准；相似组不等同于重复图片，离群不代表实验异常。",
    ]
    grouped = [g for g in groups if len(g) > 1]
    for number, group in enumerate(grouped, 1):
        minimum = min(scores[i][j] for i in group for j in group if i < j)
        refs = "、".join(f"[图片 ID: {ids[i]}]" for i in group)
        lines.append(f"- 相似组 {number}：{refs}；组内最低相似度 {minimum:.3f}。")
    if not grouped:
        lines.append("- 当前已知证据未形成满足阈值的多图相似组。")
    isolated = []
    for i in sorted(range(n), key=lambda i: int(ids[i])):
        others = [scores[i][j] for j in range(n) if i != j]
        if n >= 3 and all(v is not None for v in others) and max(others) < .3:
            isolated.append(i)
            lines.append(f"- 离群候选：[图片 ID: {ids[i]}]；最高相似度 {max(others):.3f}，证据覆盖 {n-1}/{n-1}。")
    if not isolated:
        lines.append("- 当前证据未形成满足条件的离群候选；缺失向量不作为离群依据。")
    return "\n".join(lines)
