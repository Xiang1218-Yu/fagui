from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models import Document, Regulation, Snapshot, Source, User
from app.schemas import DocumentOut, RegulationOut, SnapshotOut
from app.services.storage import read_text, resolve_path

router = APIRouter(prefix="/api", tags=["法规与快照"])


@router.get("/regulations", response_model=list[RegulationOut])
def list_regulations(
    keyword: str = "",
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    stmt = select(Regulation).order_by(Regulation.updated_at.desc())
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(or_(Regulation.title.like(like), Regulation.reg_number.like(like)))
    return list(db.scalars(stmt.limit(200)))


@router.get("/regulations/{regulation_id}")
def get_regulation(regulation_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    reg = db.get(Regulation, regulation_id)
    if reg is None:
        raise HTTPException(status_code=404, detail="法规不存在")
    docs = list(
        db.scalars(
            select(Document)
            .where(Document.regulation_id == regulation_id)
            .order_by(Document.doc_type.desc(), Document.id)
        )
    )
    source_ids = {d.source_id for d in docs}
    sources = {s.id: s.name for s in db.scalars(select(Source).where(Source.id.in_(source_ids)))}
    return {
        "regulation": RegulationOut.model_validate(reg),
        "documents": [
            {
                **DocumentOut.model_validate(d).model_dump(),
                "source_name": sources.get(d.source_id, ""),
                "snapshot_count": len(d.snapshots),
            }
            for d in docs
        ],
        "source_count": len(source_ids),
    }


@router.get("/documents", response_model=list[DocumentOut])
def list_documents(
    regulation_id: int | None = None,
    source_id: int | None = None,
    doc_type: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    stmt = select(Document).order_by(Document.last_seen_at.desc()).limit(300)
    if regulation_id is not None:
        stmt = stmt.where(Document.regulation_id == regulation_id)
    if source_id is not None:
        stmt = stmt.where(Document.source_id == source_id)
    if doc_type:
        stmt = stmt.where(Document.doc_type == doc_type)
    return list(db.scalars(stmt))


@router.get("/documents/{document_id}", response_model=DocumentOut)
def get_document(document_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="文档不存在")
    return doc


@router.get("/documents/{document_id}/snapshots", response_model=list[SnapshotOut])
def list_snapshots(document_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="文档不存在")
    return list(
        db.scalars(
            select(Snapshot).where(Snapshot.document_id == document_id).order_by(Snapshot.id.desc())
        )
    )


@router.get("/snapshots/{snapshot_id}/text", response_class=PlainTextResponse)
def snapshot_text(snapshot_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    snap = db.get(Snapshot, snapshot_id)
    if snap is None:
        raise HTTPException(status_code=404, detail="快照不存在")
    return read_text(snap.text_path) or "[该快照为二进制附件，无抽取文本，请下载原始文件核验]"


@router.get("/snapshots/{snapshot_id}/raw")
def snapshot_raw(snapshot_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    snap = db.get(Snapshot, snapshot_id)
    if snap is None:
        raise HTTPException(status_code=404, detail="快照不存在")
    path = resolve_path(snap.raw_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="快照原始文件已丢失")
    filename = path.name
    return FileResponse(path, media_type=snap.content_type or "application/octet-stream", filename=filename)
