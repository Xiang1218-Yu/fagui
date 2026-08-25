from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import Document, Regulation, User
from app.schemas.schemas import DocumentOut, RegulationOut

router = APIRouter(prefix="/regulations", tags=["regulations"])


@router.get("", response_model=list[RegulationOut])
def list_regulations(db: Session = Depends(get_db),
                     _: User = Depends(get_current_user)):
    return db.execute(select(Regulation).order_by(Regulation.id.desc())).scalars().all()


@router.get("/{regulation_id}/documents", response_model=list[DocumentOut])
def regulation_documents(regulation_id: int, db: Session = Depends(get_db),
                         _: User = Depends(get_current_user)):
    """List every source document merged under one canonical regulation –
    this is how an analyst sees that the same regulation was reposted by
    multiple sources and where each version came from."""
    reg = db.get(Regulation, regulation_id)
    if reg is None:
        raise HTTPException(404, "regulation not found")
    return db.execute(
        select(Document).where(Document.regulation_id == regulation_id).order_by(Document.id)
    ).scalars().all()


docs_router = APIRouter(prefix="/documents", tags=["documents"])


@docs_router.get("", response_model=list[DocumentOut])
def list_documents(source_id: int | None = None, db: Session = Depends(get_db),
                   _: User = Depends(get_current_user)):
    stmt = select(Document).order_by(Document.last_seen_at.desc())
    if source_id is not None:
        stmt = select(Document).where(Document.source_id == source_id).order_by(
            Document.last_seen_at.desc()
        )
    return db.execute(stmt).scalars().all()


@docs_router.get("/{document_id}", response_model=DocumentOut)
def get_document(document_id: int, db: Session = Depends(get_db),
                 _: User = Depends(get_current_user)):
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(404, "document not found")
    return doc
