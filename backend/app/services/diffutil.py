import difflib
from typing import Optional


def unified_diff_text(old_text: Optional[str], new_text: Optional[str], max_lines: int = 400) -> Optional[str]:
    """生成 unified diff 文本，限制行数避免响应过大；任一文本缺失返回 None。"""
    if old_text is None or new_text is None:
        return None
    diff = list(
        difflib.unified_diff(
            old_text.splitlines(),
            new_text.splitlines(),
            fromfile="old",
            tofile="new",
            lineterm="",
        )
    )
    if len(diff) > max_lines:
        diff = diff[:max_lines] + [f"...（差异过长，仅展示前 {max_lines} 行）"]
    return "\n".join(diff)


def diff_summary(old_text: Optional[str], new_text: Optional[str], max_samples: int = 3) -> str:
    """基于 unified_diff 统计生成中文摘要，如：新增12行/删除3行，首处变更：新增「…」。"""
    old_lines = (old_text or "").splitlines()
    new_lines = (new_text or "").splitlines()
    diff = list(difflib.unified_diff(old_lines, new_lines, lineterm=""))
    # 排除 +++/--- 文件头
    changes = [ln for ln in diff if (ln.startswith("+") and not ln.startswith("+++")) or (ln.startswith("-") and not ln.startswith("---"))]
    adds = [ln for ln in changes if ln.startswith("+")]
    dels = [ln for ln in changes if ln.startswith("-")]
    if not changes:
        return "无实质文本差异"
    parts = [f"新增{len(adds)}行/删除{len(dels)}行"]
    first = changes[0]
    preview = first[1:].strip()[:50]
    mark = "新增" if first.startswith("+") else "删除"
    parts.append(f"首处变更：{mark}「{preview}」")
    if len(changes) > 1:
        rest = []
        for ln in changes[1 : max_samples]:
            rest.append(("+" if ln.startswith("+") else "-") + ln[1:].strip()[:30])
        if rest:
            parts.append("其他变更：" + "；".join(rest))
    return "，".join(parts)
