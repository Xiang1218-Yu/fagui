import difflib


def unified_diff(old_text: str, new_text: str, fromfile: str = "旧版本", tofile: str = "新版本") -> str:
    old_lines = old_text.splitlines()
    new_lines = new_text.splitlines()
    diff = difflib.unified_diff(old_lines, new_lines, fromfile=fromfile, tofile=tofile, lineterm="")
    return "\n".join(diff)


def line_diff(old_text: str, new_text: str) -> list[dict]:
    old_lines = old_text.splitlines()
    new_lines = new_text.splitlines()
    matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
    rows: list[dict] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for i, j in zip(range(i1, i2), range(j1, j2)):
                rows.append({"type": "equal", "old_no": i + 1, "new_no": j + 1, "old": old_lines[i], "new": new_lines[j]})
        elif tag == "replace":
            old_block = old_lines[i1:i2]
            new_block = new_lines[j1:j2]
            for k in range(max(len(old_block), len(new_block))):
                rows.append(
                    {
                        "type": "replace",
                        "old_no": i1 + k + 1 if k < len(old_block) else None,
                        "new_no": j1 + k + 1 if k < len(new_block) else None,
                        "old": old_block[k] if k < len(old_block) else "",
                        "new": new_block[k] if k < len(new_block) else "",
                    }
                )
        elif tag == "delete":
            for i in range(i1, i2):
                rows.append({"type": "delete", "old_no": i + 1, "new_no": None, "old": old_lines[i], "new": ""})
        elif tag == "insert":
            for j in range(j1, j2):
                rows.append({"type": "insert", "old_no": None, "new_no": j + 1, "old": "", "new": new_lines[j]})
    return rows


def compare_attachment_sets(old_set: list[dict], new_set: list[dict]) -> dict:
    old_by_url = {item["url"]: item for item in old_set}
    new_by_url = {item["url"]: item for item in new_set}
    added = [item for url, item in new_by_url.items() if url not in old_by_url]
    removed = [item for url, item in old_by_url.items() if url not in new_by_url]
    modified = []
    for url, new_item in new_by_url.items():
        old_item = old_by_url.get(url)
        if old_item and old_item.get("content_hash") != new_item.get("content_hash"):
            modified.append(
                {
                    "url": url,
                    "name": new_item.get("name") or old_item.get("name", ""),
                    "old_hash": old_item.get("content_hash", ""),
                    "new_hash": new_item.get("content_hash", ""),
                    "old_text_hash": old_item.get("text_hash", ""),
                    "new_text_hash": new_item.get("text_hash", ""),
                }
            )
    return {"added": added, "removed": removed, "modified": modified}


def summarize_change(changed_fields: dict) -> str:
    parts = []
    if changed_fields.get("body_changed"):
        parts.append("正文内容发生修订")
    if changed_fields.get("title_changed"):
        parts.append(f"标题由「{changed_fields.get('old_title', '')}」变更为「{changed_fields.get('new_title', '')}」")
    att = changed_fields.get("attachments") or {}
    if att.get("added"):
        parts.append(f"新增附件 {len(att['added'])} 个")
    if att.get("modified"):
        parts.append(f"附件内容更新 {len(att['modified'])} 个")
    if att.get("removed"):
        parts.append(f"附件移除 {len(att['removed'])} 个")
    return "；".join(parts) or "页面内容发生变化"
