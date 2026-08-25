from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Change, Document, Regulation, Source
from app.schemas import ChangeListItem, RegulationDetail, RegulationOut

router = APIRouter(prefix="/regulations", tags=["regulations"])


def _agg_map(db: Session):
    """各法规的变更总数、待审核数、最近变更时间。"""
    rows = db.execute(
        select(
            Change.regulation_id,
            func.count(Change.id),
            func.sum(case((Change.status == "pending_review", 1), else_=0)),
            func.max(Change.detected_at),
        ).group_by(Change.regulation_id)
    ).all()
    return {reg_id: (total, pending or 0, latest) for reg_id, total, pending, latest in rows}


def _to_out(reg: Regulation, agg) -> RegulationOut:
    total, pending, latest = agg.get(reg.id, (0, 0, None))
    return RegulationOut(
        id=reg.id,
        canonical_title=reg.canonical_title,
        regulation_no=reg.regulation_no,
        authority=reg.authority,
        change_count=total,
        pending_count=pending,
        latest_change_at=latest,
    )


@router.get("", response_model=list[RegulationOut])
def list_regulations(db: Session = Depends(get_db)):
    regs = db.scalars(select(Regulation).order_by(Regulation.id)).all()
    agg = _agg_map(db)
    return [_to_out(reg, agg) for reg in regs]


@router.get("/{regulation_id}", response_model=RegulationDetail)
def get_regulation(regulation_id: int, db: Session = Depends(get_db)):
    reg = db.get(Regulation, regulation_id)
    if reg is None:
        raise HTTPException(status_code=404, detail="法规不存在")
    agg = _agg_map(db)
    rows = db.execute(
        select(Change, Regulation, Document, Source)
        .join(Regulation, Change.regulation_id == Regulation.id)
        .join(Document, Change.document_id == Document.id)
        .join(Source, Document.source_id == Source.id)
        .where(Change.regulation_id == regulation_id)
        .order_by(Change.detected_at.desc(), Change.id.desc())
    ).all()
    changes = [
        ChangeListItem(
            id=change.id,
            regulation_id=change.regulation_id,
            regulation_title=regulation.canonical_title,
            document_url=document.url,
            source_name=source.name,
            change_type=change.change_type,
            status=change.status,
            diff_summary=change.diff_summary,
            detected_at=change.detected_at,
        )
        for change, regulation, document, source in rows
    ]
    return RegulationDetail(**_to_out(reg, agg).model_dump(), changes=changes)
