from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional

from app.database import get_db
from app.models import ImpactAssessment, Regulation, Change
from app.schemas import (
    ImpactAssessmentCreate, ImpactAssessmentUpdate,
    ImpactAssessmentResponse, PaginatedResponse
)

router = APIRouter(prefix="/api/impact-assessments", tags=["影响研判"])


@router.get("", response_model=PaginatedResponse)
def list_assessments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    regulation_id: Optional[str] = None,
    overall_level: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(ImpactAssessment)
    if regulation_id:
        query = query.filter(ImpactAssessment.regulation_id == regulation_id)
    if overall_level:
        query = query.filter(ImpactAssessment.overall_level == overall_level)
    if status:
        query = query.filter(ImpactAssessment.status == status)

    total = query.count()
    assessments = (
        query.order_by(desc(ImpactAssessment.updated_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return PaginatedResponse(
        items=[ImpactAssessmentResponse.model_validate(a) for a in assessments],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.post("", response_model=ImpactAssessmentResponse, status_code=201)
def create_assessment(data: ImpactAssessmentCreate, db: Session = Depends(get_db)):
    regulation_id = None
    if data.change_id:
        change = db.query(Change).filter(Change.id == data.change_id).first()
        if not change:
            raise HTTPException(status_code=404, detail="关联变更不存在")
        regulation_id = change.regulation_id
    else:
        raise HTTPException(status_code=400, detail="必须关联变更记录")

    existing = (
        db.query(ImpactAssessment)
        .filter(ImpactAssessment.change_id == data.change_id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="该变更已有影响研判记录")

    assessment = ImpactAssessment(
        regulation_id=regulation_id,
        change_id=data.change_id,
        overall_level=data.overall_level,
        affected_teams=data.affected_teams,
        affected_systems=data.affected_systems,
        affected_products=data.affected_products,
        compliance_areas=data.compliance_areas,
        analysis=data.analysis,
        required_actions=data.required_actions,
        deadline=data.deadline,
        estimated_effort=data.estimated_effort,
        assessor_id=data.assessor_id,
        assessor_name=data.assessor_name,
        status="draft",
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    return assessment


@router.get("/{assessment_id}", response_model=ImpactAssessmentResponse)
def get_assessment(assessment_id: str, db: Session = Depends(get_db)):
    assessment = db.query(ImpactAssessment).filter(ImpactAssessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="影响研判记录不存在")
    return assessment


@router.put("/{assessment_id}", response_model=ImpactAssessmentResponse)
def update_assessment(
    assessment_id: str,
    data: ImpactAssessmentUpdate,
    db: Session = Depends(get_db),
):
    assessment = db.query(ImpactAssessment).filter(ImpactAssessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="影响研判记录不存在")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if value is not None:
            setattr(assessment, key, value)

    from datetime import datetime
    assessment.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(assessment)
    return assessment


@router.post("/{assessment_id}/submit", response_model=ImpactAssessmentResponse)
def submit_assessment(assessment_id: str, db: Session = Depends(get_db)):
    assessment = db.query(ImpactAssessment).filter(ImpactAssessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="影响研判记录不存在")
    assessment.status = "submitted"
    from datetime import datetime
    assessment.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(assessment)
    return assessment
