"""Text diff and regulation dedup helpers."""
from __future__ import annotations

import difflib
import hashlib
import re


def sha256_hex(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def similarity_ratio(old: str, new: str) -> float:
    return difflib.SequenceMatcher(None, old, new).ratio()


def unified_diff(old: str, new: str, context: int = 3) -> str:
    diff = difflib.unified_diff(
        old.splitlines(),
        new.splitlines(),
        fromfile="previous",
        tofile="current",
        lineterm="",
        n=context,
    )
    return "\n".join(diff)


def summarize_diff(old: str, new: str, max_lines: int = 6) -> str:
    """Produce a short human summary of what changed."""
    added = 0
    removed = 0
    sample_added: list[str] = []
    sample_removed: list[str] = []
    for line in difflib.ndiff(old.splitlines(), new.splitlines()):
        if line.startswith("+ "):
            added += 1
            if len(sample_added) < max_lines and line[2:].strip():
                sample_added.append(line[2:].strip())
        elif line.startswith("- "):
            removed += 1
            if len(sample_removed) < max_lines and line[2:].strip():
                sample_removed.append(line[2:].strip())
    parts = [f"新增 {added} 行，删除 {removed} 行。"]
    if sample_added:
        parts.append("新增示例: " + " / ".join(sample_added[:3]))
    if sample_removed:
        parts.append("删除示例: " + " / ".join(sample_removed[:3]))
    return " ".join(parts)


_norm_re = re.compile(r"[\s\u3000·・.,，。;；:：!！?？（）()\[\]【】\"'“”‘’—\-_/\\|]+")
_noise_re = re.compile(r"(关于|印发|的通知|的公告|的决定|征求意见稿|试行|修订版|正式稿)")


def normalize_title(title: str) -> str:
    """Normalize a regulation title into a dedup key so the same regulation
    reported by several sources maps to one canonical regulation."""
    t = title or ""
    t = _noise_re.sub("", t)
    t = _norm_re.sub("", t)
    t = t.lower().strip()
    return t[:120]


def dedup_key_for(title: str, identifier: str = "") -> str:
    ident = _norm_re.sub("", (identifier or "").lower())
    base = normalize_title(title)
    if ident:
        return f"{base}#{ident}"
    return base
