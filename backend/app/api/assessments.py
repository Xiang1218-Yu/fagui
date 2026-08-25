from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Assessment, Change, Regulation, User
from app.schemas import AssessmentCreate, AssessmentOut, AssessmentUpdate
from app.security import get_current_user, require_roles

router = APIRouter(prefix="/assessments", tags=["assessments"], dependencies=[Depends(get_current_user)])


def _to_out(assessment: Assessment, regulation_title: str) -> AssessmentOut:
    return AssessmentOut(
        id=assessment.id,
        change_id=assessment.change_id,
        regulation_title=regulation_title,
        business_area=assessment.business_area,
        impact_level=assessment.impact_level,
        analysis=assessment.analysis,
        recommendation=assessment.recommendation,
        created_by=assessment.created_by,
        created_at=assessment.created_at,
    )


def _regulation_title(db: Session, change_id: int) -> Optional[str]:
    return db.scalar(
        select(Regulation.canonical_title)
        .join(Change, Change.regulation_id == Regulation.id)
        .where(Change.id == change_id)
    )


@router.get("", response_model=list[AssessmentOut])
def list_assessments(change_id: Optional[int] = None, db: Session = Depends(get_db)):
    stmt = (
        select(Assessment, Regulation.canonical_title)
        .join(Change, Assessment.change_id == Change.id)
        .join(Regulation, Change.regulation_id == Regulation.id)
        .order_by(Assessment.id.desc())
    )
    if change_id is not None:
        stmt = stmt.where(Assessment.change_id == change_id)
    return [_to_out(a, title) for a, title in db.execute(stmt).all()]


@router.post("", response_model=AssessmentOut)
def create_assessment(
    payload: AssessmentCreate, db: Session = Depends(get_db), _: User = Depends(require_roles("admin", "analyst"))
):
    change = db.get(Change, payload.change_id)
    if change is None:
        raise HTTPException(status_code=404, detail="变更不存在")
    assessment = Assessment(**payload.model_dump())
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    return _to_out(assessment, _regulation_title(db, assessment.change_id) or "")


@router.patch("/{assessment_id}", response_model=AssessmentOut)
def update_assessment(
    assessment_id: int,
    payload: AssessmentUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "analyst")),
):
    assessment = db.get(Assessment, assessment_id)
    if assessment is None:
        raise HTTPException(status_code=404, detail="研判不存在")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(assessment, key, value)
    db.commit()
    db.refresh(assessment)
    return _to_out(assessment, _regulation_title(db, assessment.change_id) or "")
