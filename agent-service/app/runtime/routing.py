"""Conservative request routing: unknown requests never imply asset search."""
import re


def general_route(query: str) -> str | None:
    text = re.sub(r"\s+", "", query).lower()
    authorized_scope = "空间" in text and any(word in text for word in (
        "授权", "有权限", "可访问", "可以访问", "能访问", "能查看", "可查看", "我的", "我有"))
    usage_request = any(word in text for word in (
        "使用情况", "使用状况", "用量", "容量", "占用", "剩余", "使用率", "图片数量", "多少张", "多少图片", "资产数量"))
    # A directory-wide usage request is distinct from single-space statistics.
    # Explicit image searches and filtered/trend analysis retain their own routes.
    if authorized_scope and usage_request and not any(word in text for word in (
        "查找", "搜索", "检索", "趋势", "分布", "最近", "本月", "上月", "今天", "昨天", "比较空间")):
        return "accessible_space_usage"
    if "空间" in text and any(word in text for word in (
        "有哪些", "哪些空间", "空间列表", "列出", "有权限", "被授权", "可访问", "能访问", "能查看", "有几个空间")):
        # Do not turn an explicit request for pictures in those spaces into a directory lookup.
        if not any(word in text for word in ("图片", "照片", "图像", "统计", "容量", "比较")):
            return "accessible_spaces"
    if any(word in text for word in ("你能做什么", "你有什么功能", "有哪些工具", "怎么使用", "使用说明", "你是谁", "你好", "谢谢")):
        return "capabilities"
    return None


def is_search_request(query: str) -> bool:
    return any(word in query.lower() for word in (
        "图片", "照片", "图像", "截图", "查找", "搜索", "检索", "找相似", "找图", "张图",
        "实验图", "第", "再找", "换一批", "只看", "排除", "筛选", "河道", "显微", "image", "search"))


def compose_spaces(spaces) -> str:
    labels = {"picture:view": "查看图片", "picture:upload": "上传图片",
              "picture:edit": "编辑图片", "picture:delete": "删除图片", "spaceUser:manage": "管理成员"}
    lines = [f"当前账号可查看的空间共 {len(spaces)} 个：", ""]
    for index, space in enumerate(spaces, 1):
        # Names are data, not model instructions or Markdown links.
        name = re.sub(r"[\r\n\[\]<>`*]", " ", space.spaceName).strip() or "未命名空间"
        permissions = "、".join(labels[p] for p in space.permissions if p in labels)
        kind = "团队空间" if space.spaceType == 1 else "个人空间"
        lines.append(f"{index}. {name}（{kind}）\n   权限：{permissions or '查看图片'}")
    if not spaces:
        lines.append("目前没有可查看的个人或团队空间。")
    lines.extend(["", "此外可查看已审核的公共图库图片。以上为当前账号实时权限，不会改变本会话的图片检索范围。"])
    return "\n".join(lines)


def compose_space_usage(spaces) -> str:
    def size(value):
        if value is None:
            return "未知"
        for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
            if value < 1024 or unit == "TiB":
                return f"{value:.2f} {unit}"
            value /= 1024

    def ratio(used, maximum):
        return f"{used / maximum:.1%}" if used is not None and maximum and maximum > 0 else "未知"

    def count(value):
        return str(value) if value is not None else "未知"

    if not spaces:
        return "当前账号没有可查看的个人或团队空间，暂无空间使用情况可统计。公共图库不计入个人或团队空间配额。"
    lines = [f"你当前可查看的 {len(spaces)} 个空间使用情况如下：", "",
             "| 空间名称 | 图片数 / 上限 | 已用容量 / 上限 | 容量使用率 | 剩余容量 |",
             "|---|---:|---:|---:|---:|"]
    for space in spaces:
        name = re.sub(r"[\r\n|\[\]<>`*]", " ", space.spaceName).strip() or "未命名空间"
        remaining = max(0, space.maxSize - space.totalSize) if space.maxSize is not None and space.totalSize is not None else None
        lines.append(f"| {name} | {count(space.totalCount)} / {count(space.maxCount)} | {size(space.totalSize)} / {size(space.maxSize)} | {ratio(space.totalSize, space.maxSize)} | {size(remaining)} |")
    lines.append("")
    if all(s.totalSize is not None and s.totalCount is not None for s in spaces):
        lines.append(f"合计：{sum(s.totalCount for s in spaces)} 张图片，已使用 {size(sum(s.totalSize for s in spaces))}。")
    else:
        lines.append("部分空间用量暂不可用，未将未知值当作零计算总量；若刚更新代码，请确认 DDD 后端已重启。")
    crowded = sum(1 for s in spaces if (s.maxSize and s.totalSize is not None and s.totalSize >= s.maxSize * .8)
                  or (s.maxCount and s.totalCount is not None and s.totalCount >= s.maxCount * .8))
    if crowded:
        lines.append(f"有 {crowded} 个空间的容量或图片数量已达到配额的 80%，建议检查并按需清理或扩容。")
    lines.append("\n以上来自当前权限复核后的空间用量计数，包含个人及团队空间，不含公共图库；不是历史趋势统计，也不会改变本会话的检索范围。")
    return "\n".join(lines)
