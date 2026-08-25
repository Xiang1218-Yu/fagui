import hashlib
import os
from pathlib import Path

from app.config import settings


def _root() -> Path:
    root = Path(settings.storage_dir)
    root.mkdir(parents=True, exist_ok=True)
    return root


def content_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def save_raw(source_id: int, document_id: int, snapshot_id: int, ext: str, content: bytes) -> str:
    folder = _root() / f"source_{source_id}" / f"doc_{document_id}"
    folder.mkdir(parents=True, exist_ok=True)
    path = (folder / f"snapshot_{snapshot_id}{ext}").resolve()
    path.write_bytes(content)
    return str(path)


def save_text(source_id: int, document_id: int, snapshot_id: int, text: str) -> str:
    folder = _root() / f"source_{source_id}" / f"doc_{document_id}"
    folder.mkdir(parents=True, exist_ok=True)
    path = (folder / f"snapshot_{snapshot_id}.txt").resolve()
    path.write_text(text, encoding="utf-8")
    return str(path)


def read_text(path: str) -> str:
    if not path:
        return ""
    p = Path(path)
    if not p.exists():
        return ""
    return p.read_text(encoding="utf-8", errors="replace")


def resolve_path(path: str) -> Path:
    return Path(path)
