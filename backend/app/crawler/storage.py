"""Snapshot storage – persists raw bytes and extracted text to disk for traceability."""
from __future__ import annotations

import os
from datetime import datetime

from app.core.config import settings


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def store_snapshot(source_id: int, document_url: str, kind: str, raw: bytes, text: str,
                   content_hash: str) -> tuple[str, str]:
    """Write raw + text snapshot files, return (raw_path, text_path)."""
    day = datetime.utcnow().strftime("%Y%m%d")
    folder = os.path.join(settings.snapshot_dir, str(source_id), day)
    _ensure_dir(folder)

    base = content_hash[:16]
    raw_path = os.path.join(folder, f"{kind}_{base}.raw")
    text_path = os.path.join(folder, f"{kind}_{base}.txt")

    try:
        with open(raw_path, "wb") as f:
            f.write(raw)
        with open(text_path, "w", encoding="utf-8") as f:
            f.write(text)
    except OSError:
        # storage failure should not break crawl; return empty paths
        return "", ""
    return raw_path, text_path


def read_text(text_path: str) -> str:
    if not text_path or not os.path.exists(text_path):
        return ""
    try:
        with open(text_path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""
