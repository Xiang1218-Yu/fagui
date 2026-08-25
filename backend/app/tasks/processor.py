import logging
from datetime import datetime
from celery import shared_task
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Attachment, Regulation, Change
from app.services.parser import ContentParser
from app.services.merger import RegulationMerger

logger = logging.getLogger(__name__)


@shared_task(name="app.tasks.processor.reprocess_attachment")
def reprocess_attachment(attachment_id: str) -> dict:
    db = SessionLocal()
    try:
        attachment = db.query(Attachment).filter(Attachment.id == attachment_id).first()
        if not attachment:
            return {"error": "Attachment not found"}

        if not attachment.storage_path:
            return {"error": "Attachment file not found in storage"}

        from app.services.storage import SnapshotStorage
        storage = SnapshotStorage()
        content = storage.load_attachment(attachment.storage_path)
        if not content:
            return {"error": "Failed to read attachment file"}

        parser = ContentParser()
        extracted_text, status = parser.parse_attachment_text(
            content, attachment.content_type or "", attachment.filename
        )

        attachment.extracted_text = extracted_text[:100000] if extracted_text else None
        attachment.extraction_status = status
        attachment.extraction_error = None if status == "success" else status
        db.commit()

        return {
            "attachment_id": attachment_id,
            "status": status,
            "text_length": len(extracted_text) if extracted_text else 0,
        }
    except Exception as e:
        logger.error(f"Failed to reprocess attachment {attachment_id}: {e}")
        return {"error": str(e)}
    finally:
        db.close()


@shared_task(name="app.tasks.processor.run_deduplication")
def run_deduplication() -> dict:
    db = SessionLocal()
    try:
        merger = RegulationMerger(db)
        regulations = (
            db.query(Regulation)
            .filter(Regulation.is_primary == True)
            .order_by(Regulation.first_seen_at.desc())
            .limit(500)
            .all()
        )

        merged_count = 0
        for reg in regulations:
            try:
                result = merger.auto_merge(reg, threshold=0.85)
                if result:
                    merged_count += 1
            except Exception as e:
                logger.warning(f"Deduplication failed for regulation {reg.id}: {e}")

        return {"processed": len(regulations), "merged": merged_count}
    finally:
        db.close()
