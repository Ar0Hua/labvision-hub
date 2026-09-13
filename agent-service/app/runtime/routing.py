"""Conservative request routing: unknown requests never imply asset search."""
import re


def general_route(query: str) -> str | None:
    text = re.sub(r"\s+", "", query).lower()
    if "空间" in text and any(word in text for word in (
        "有哪些", "哪些空间", "空间列表", "列出", "有权限", "可访问", "能访问", "能查看", "有几个空间")):
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
