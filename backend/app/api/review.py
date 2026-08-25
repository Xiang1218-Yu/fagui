from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models import Change, ReviewTask, Source, User
from app.schemas import ReviewDecisionRequest, ReviewTaskOut
from app.services.notifier import dispatch_event

router = APIRouter(prefix="/api/review", tags=["复核队列"])

DECISION_MAP = {
    "confirm": ("confirmed", "确认变更属实"),
    "need_followup": ("confirmed", "确认变更，需持续跟踪"),
    "false_positive": ("dismissed", "判定为误报/无需处理"),
}


@router.get("/tasks", response_model=list[dict])
def list_tasks(
    status_filter: str = "pending",
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    stmt = (
        select(ReviewTask, Change, Source)
        .join(Change, Change.id == ReviewTask.change_id)
        .join(Source, Source.id == Change.source_id)
        .order_by(ReviewTask.id.desc())
        .limit(300)
    )
    if status_filter and status_filter != "all":
        stmt = stmt.where(ReviewTask.status == status_filter)
    result = []
    for task, change, source in db.execute(stmt):
        result.append(
            {
                **ReviewTaskOut.model_validate(task).model_dump(),
                "change_title": change.title,
                "change_type": change.change_type,
                "severity": change.severity,
                "change_status": change.status,
                "summary": change.summary,
                "source_name": source.name,
                "detected_at": change.detected_at,
                "assignee_name": task.assignee.display_name if task.assignee else None,
            }
        )
    return result


@router.post("/tasks/{task_id}/claim", response_model=ReviewTaskOut)
def claim_task(task_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    task = db.get(ReviewTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="复核任务不存在")
    if task.status not in ("pending", "claimed"):
        raise HTTPException(status_code=400, detail="该任务已出具结论")
    task.status = "claimed"
    task.assignee_id = user.id
    task.claimed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(task)
    return task


@router.post("/tasks/{task_id}/decide", response_model=ReviewTaskOut)
def decide_task(
    task_id: int,
    payload: ReviewDecisionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    task = db.get(ReviewTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="复核任务不存在")
    if task.status in ("approved", "dismissed"):
        raise HTTPException(status_code=400, detail="该任务已出具结论")
    if payload.decision not in DECISION_MAP:
        raise HTTPException(status_code=400, detail="结论类型无效")

    change_status, _ = DECISION_MAP[payload.decision]
    change = db.get(Change, task.change_id)
    task.status = "approved" if change_status == "confirmed" else "dismissed"
    task.decision = payload.decision
    task.comment = payload.comment
    task.assignee_id = task.assignee_id or user.id
    task.decided_at = datetime.now(timezone.utc)
    if change:
        change.status = change_status
        change.decided_at = task.decided_at
        source = db.get(Source, change.source_id)
        dispatch_event(
            db,
            event_type="review_decided",
            title=f"复核结论：{change.title}",
            body=(
                f"来源：{source.name if source else ''}\n"
                f"结论：{dict(confirm='确认变更', need_followup='确认并跟踪', false_positive='误报')[payload.decision]}\n"
                f"备注：{payload.comment or '（无）'}"
            ),
            data={"change_id": change.id, "decision": payload.decision},
            source_id=change.source_id,
        )
    db.commit()
    db.refresh(task)
    return task
