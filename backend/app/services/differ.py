import difflib
import hashlib
import re
from typing import Any, Optional
from dataclasses import dataclass, field


@dataclass
class DiffStats:
    lines_added: int = 0
    lines_removed: int = 0
    lines_changed: int = 0
    total_before: int = 0
    total_after: int = 0
    change_ratio: float = 0.0


@dataclass
class ChangeSection:
    section_type: str
    header: str
    before_text: str
    after_text: str
    lines: list[dict[str, Any]] = field(default_factory=list)


class DiffEngine:
    def compute_text_diff(self, before: str, after: str) -> dict[str, Any]:
        before_lines = before.splitlines() if before else []
        after_lines = after.splitlines() if after else []

        before_normalized = [self._normalize_line(l) for l in before_lines]
        after_normalized = [self._normalize_line(l) for l in after_lines]

        before_set = set(before_normalized)
        after_set = set(after_normalized)

        removed = before_set - after_set
        added = after_set - before_set

        stats = DiffStats(
            lines_added=len(added),
            lines_removed=len(removed),
            total_before=len(before_lines),
            total_after=len(after_lines),
        )

        if max(stats.total_before, stats.total_after) > 0:
            stats.change_ratio = (stats.lines_added + stats.lines_removed) / max(
                stats.total_before, stats.total_after
            )
        stats.lines_changed = len(added) + len(removed)

        differ = difflib.HtmlDiff(wrapcolumn=100)
        diff_html = differ.make_table(
            before_lines, after_lines,
            fromdesc="之前版本", todesc="当前版本",
            context=True, numlines=3
        )

        unified_diff = list(difflib.unified_diff(
            before_lines, after_lines,
            fromfile="before", tofile="after",
            lineterm=""
        ))

        sections = self._identify_changed_sections(before_lines, after_lines)

        severity = self._assess_severity(stats, sections, before, after)

        return {
            "diff_html": diff_html,
            "unified_diff": unified_diff[:500],
            "stats": {
                "lines_added": stats.lines_added,
                "lines_removed": stats.lines_removed,
                "lines_changed": stats.lines_changed,
                "total_before": stats.total_before,
                "total_after": stats.total_after,
                "change_ratio": round(stats.change_ratio, 4),
            },
            "sections": sections[:20],
            "severity": severity,
            "before_hash": hashlib.sha256(before.encode("utf-8")).hexdigest() if before else None,
            "after_hash": hashlib.sha256(after.encode("utf-8")).hexdigest() if after else None,
        }

    def _normalize_line(self, line: str) -> str:
        return re.sub(r"\s+", " ", line.strip())

    def _identify_changed_sections(
        self, before_lines: list[str], after_lines: list[str]
    ) -> list[dict[str, Any]]:
        sections = []
        matcher = difflib.SequenceMatcher(None, before_lines, after_lines, autojunk=False)

        for op, i1, i2, j1, j2 in matcher.get_opcodes():
            if op == "equal":
                continue
            before_text = "\n".join(before_lines[max(0, i1 - 2):min(len(before_lines), i2 + 2)])
            after_text = "\n".join(after_lines[max(0, j1 - 2):min(len(after_lines), j2 + 2)])

            header_before = self._find_section_header(before_lines, i1)
            header_after = self._find_section_header(after_lines, j1)
            header = header_after or header_before or "变更部分"

            diff_lines = []
            if op in ("replace", "delete"):
                for line in before_lines[i1:i2]:
                    diff_lines.append({"type": "removed", "text": line})
            if op in ("replace", "insert"):
                for line in after_lines[j1:j2]:
                    diff_lines.append({"type": "added", "text": line})

            sections.append({
                "section_type": op,
                "header": header,
                "before_context": before_text[:2000],
                "after_context": after_text[:2000],
                "lines": diff_lines[:100],
            })

        return sections

    def _find_section_header(self, lines: list[str], position: int) -> Optional[str]:
        for i in range(position, max(-1, position - 20), -1):
            if i < 0 or i >= len(lines):
                continue
            line = lines[i].strip()
            if not line:
                continue
            if re.match(r"^(第[一二三四五六七八九十百千]+[章节条]|[一二三四五六七八九十]+[、.]|\d+[.、]\s*|Article\s+\d+)", line):
                return line[:200]
            if len(line) < 80 and (line.endswith("：") or line.endswith(":")):
                return line[:200]
        return None

    def _assess_severity(
        self, stats: DiffStats, sections: list[dict], before: str, after: str
    ) -> str:
        ratio = stats.change_ratio

        critical_keywords = [
            "废止", "失效", "撤销", "立即执行", "重大变化", "处罚", "罚款",
            "repeal", "rescind", "immediate", "penalty", "fine", "critical"
        ]
        high_keywords = [
            "修订", "修正", "新增", "删除", "变更", "调整", "施行",
            "amend", "revise", "modify", "change", "effective"
        ]

        after_lower = after.lower()
        has_critical = any(kw in after_lower for kw in critical_keywords)
        has_high = any(kw in after_lower for kw in high_keywords)

        if has_critical or ratio > 0.5:
            return "critical"
        elif has_high or ratio > 0.2:
            return "high"
        elif ratio > 0.05:
            return "medium"
        else:
            return "low"

    def compare_fields(
        self, before: dict[str, Any], after: dict[str, Any]
    ) -> list[dict[str, Any]]:
        changed = []
        all_keys = set(list(before.keys()) + list(after.keys()))
        for key in all_keys:
            old_val = before.get(key)
            new_val = after.get(key)
            if old_val != new_val:
                changed.append({
                    "field": key,
                    "old_value": old_val,
                    "new_value": new_val,
                })
        return changed

    def compare_attachments(
        self, before_attachments: list[dict], after_attachments: list[dict]
    ) -> dict[str, list]:
        before_hashes = {a.get("file_hash") or a.get("url"): a for a in before_attachments}
        after_hashes = {a.get("file_hash") or a.get("url"): a for a in after_attachments}

        added = [after_hashes[h] for h in after_hashes if h not in before_hashes]
        removed = [before_hashes[h] for h in before_hashes if h not in after_hashes]
        modified = []
        for h in after_hashes:
            if h in before_hashes:
                old = before_hashes[h]
                new = after_hashes[h]
                if old.get("file_hash") != new.get("file_hash"):
                    modified.append({"before": old, "after": new})

        return {"added": added, "removed": removed, "modified": modified}
