from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models import Change, ImpactAssessment, Regulation, ReviewTask, User
from app.schemas import ImpactCreate, ImpactOut, ImpactUpdate
from app.services.notifier import dispatch_event

router = APIRouter(prefix="/api/impact", tags=["影响研判"])

ALLOWED_REVIEW_DECISIONS = ("confirm", "need_followup")


def _ensure_change_assessable(db: Session, change_id: int | None) -> Change | None:
    """仅允许复核结论为「确认变更」或「需持续跟踪」的已确认变更发起/保存/发布研判。

    待复核（pending_review）与误报（dismissed / false_positive）一律拦截。
    """
    if change_id is None:
        return None
    change = db.get(Change, change_id)
    if change is None:
        raise HTTPException(status_code=404, detail="关联变更不存在")
    review = db.scalar(select(ReviewTask).where(ReviewTask.change_id == change.id))
    decision = review.decision if review else ""
    if change.status != "confirmed" or decision not in ALLOWED_REVIEW_DECISIONS:
        reason = (
            "该变更尚未完成人工复核"
            if change.status == "pending_review"
            else "该变更已被判定为误报/无需处理"
        )
        raise HTTPException(
            status_code=400,
            detail=f"拦截：只有复核结论为「确认变更属实」或「确认，需持续跟踪」的变更才能创建、保存或发布影响研判（{reason}）",
        )
    return change


@router.get("", response_model=list[dict])
def list_assessments(
    status_filter: str = "",
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    stmt = select(ImpactAssessment).order_by(ImpactAssessment.id.desc()).limit(200)
    if status_filter:
        stmt = stmt.where(ImpactAssessment.status == status_filter)
    result = []
    for assessment in db.scalars(stmt):
        item = ImpactOut.model_validate(assessment).model_dump()
        change = db.get(Change, assessment.change_id) if assessment.change_id else None
        reg = db.get(Regulation, assessment.regulation_id) if assessment.regulation_id else None
        analyst = db.get(User, assessment.analyst_id)
        item["change_title"] = change.title if change else None
        item["regulation_title"] = reg.title if reg else (change.title if change else None)
        item["analyst_name"] = analyst.display_name or analyst.username if analyst else ""
        result.append(item)
    return result


@router.post("", response_model=ImpactOut)
def create_assessment(
    payload: ImpactCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if payload.change_id is None:
        raise HTTPException(status_code=400, detail="创建影响研判必须关联变更，且该变更须已通过人工复核")
    change = _ensure_change_assessable(db, payload.change_id)
    regulation_id = payload.regulation_id or (change.regulation_id if change else None)
    assessment = ImpactAssessment(
        change_id=payload.change_id,
        regulation_id=regulation_id,
        analyst_id=user.id,
        risk_level=payload.risk_level,
        affected_teams=payload.affected_teams,
        affected_business=payload.affected_business,
        impact_summary=payload.impact_summary,
        action_items=payload.action_items,
        status=payload.status,
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    return assessment


@router.patch("/{assessment_id}", response_model=ImpactOut)
def update_assessment(
    assessment_id: int,
    payload: ImpactUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    assessment = db.get(ImpactAssessment, assessment_id)
    if assessment is None:
        raise HTTPException(status_code=404, detail="研判记录不存在")
    _ensure_change_assessable(db, assessment.change_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(assessment, key, value)
    db.commit()
    db.refresh(assessment)
    return assessment


@router.post("/{assessment_id}/publish", response_model=ImpactOut)
def publish_assessment(
    assessment_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    assessment = db.get(ImpactAssessment, assessment_id)
    if assessment is None:
        raise HTTPException(status_code=404, detail="研判记录不存在")
    _ensure_change_assessable(db, assessment.change_id)
    assessment.status = "published"
    assessment.updated_at = datetime.now(timezone.utc)
    reg = db.get(Regulation, assessment.regulation_id) if assessment.regulation_id else None
    change = db.get(Change, assessment.change_id) if assessment.change_id else None
    title = reg.title if reg else (change.title if change else "法规")
    dispatch_event(
        db,
        event_type="impact_published",
        title=f"影响研判已发布：{title}",
        body=(
            f"风险等级：{assessment.risk_level}\n"
            f"影响团队：{', '.join(assessment.affected_teams) or '未指定'}\n"
            f"研判结论：{assessment.impact_summary or '（无）'}\n"
            f"行动项：{len(assessment.action_items)} 项"
        ),
        data={"assessment_id": assessment.id, "regulation_id": assessment.regulation_id},
        source_id=change.source_id if change else None,
    )
    db.commit()
    db.refresh(assessment)
    return assessment
