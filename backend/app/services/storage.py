import os
import json
import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Any
from app.config import settings

logger = logging.getLogger(__name__)


class SnapshotStorage:
    def __init__(self):
        self.snapshot_path = Path(settings.SNAPSHOT_STORAGE_PATH)
        self.attachment_path = Path(settings.ATTACHMENT_STORAGE_PATH)
        self.snapshot_path.mkdir(parents=True, exist_ok=True)
        self.attachment_path.mkdir(parents=True, exist_ok=True)

    def save_snapshot(
        self,
        source_id: str,
        url_hash: str,
        content_html: str,
        content_text: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        date_dir = datetime.utcnow().strftime("%Y/%m/%d")
        save_dir = self.snapshot_path / source_id / date_dir
        save_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.utcnow().strftime("%H%M%S")
        filename = f"{url_hash}_{timestamp}.json"
        filepath = save_dir / filename

        snapshot_data = {
            "url_hash": url_hash,
            "source_id": source_id,
            "captured_at": datetime.utcnow().isoformat(),
            "content_html": content_html,
            "content_text": content_text,
            "metadata": metadata or {},
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(snapshot_data, f, ensure_ascii=False)

        return str(filepath)

    def load_snapshot(self, filepath: str) -> Optional[dict[str, Any]]:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except (IOError, json.JSONDecodeError) as e:
            logger.error(f"Failed to load snapshot {filepath}: {e}")
            return None

    def save_attachment(
        self,
        source_id: str,
        filename: str,
        content: bytes,
        file_hash: str,
    ) -> str:
        date_dir = datetime.utcnow().strftime("%Y/%m/%d")
        save_dir = self.attachment_path / source_id / date_dir
        save_dir.mkdir(parents=True, exist_ok=True)

        safe_filename = self._sanitize_filename(filename)
        final_name = f"{file_hash[:16]}_{safe_filename}"
        filepath = save_dir / final_name

        if not filepath.exists():
            with open(filepath, "wb") as f:
                f.write(content)

        return str(filepath)

    def load_attachment(self, filepath: str) -> Optional[bytes]:
        try:
            with open(filepath, "rb") as f:
                return f.read()
        except IOError as e:
            logger.error(f"Failed to load attachment {filepath}: {e}")
            return None

    def _sanitize_filename(self, filename: str) -> str:
        filename = os.path.basename(filename)
        filename = "".join(c for c in filename if c.isalnum() or c in "._- ")
        return filename[:200] or "attachment"

    def hash_url(self, url: str) -> str:
        return hashlib.sha256(url.encode("utf-8")).hexdigest()
