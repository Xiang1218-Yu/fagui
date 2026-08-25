from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, require_admin
from app.models import User
from app.seed import demo_version, write_demo_site

router = APIRouter(prefix="/api/demo", tags=["演示环境"])


@router.get("/status")
def status(_: User = Depends(get_current_user)):
    return {"version": demo_version()}


@router.post("/simulate-update")
def simulate_update(_: User = Depends(require_admin)):
    write_demo_site(v2=True)
    return {"ok": True, "version": "v2", "message": "演示站点已发布法规修订：通知正文新增第十五/十六条、附件更新、新增年度检查计划，请重新触发采集"}


@router.post("/reset")
def reset(_: User = Depends(require_admin)):
    write_demo_site(v2=False)
    return {"ok": True, "version": "v1", "message": "演示站点已恢复初始版本"}
