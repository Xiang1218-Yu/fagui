from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AuthToken, User, utcnow
from app.schemas import ChangePasswordRequest, CreateUserRequest, LoginRequest, TokenResponse, UserOut
from app.security import create_token, get_current_token, get_current_user, hash_password, require_roles, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])

_TOKEN_TTL_DAYS = 7


def _to_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        username=user.username,
        role=user.role,
        must_change_password=user.must_change_password,
        created_at=user.created_at,
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.username == payload.username))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    token = AuthToken(
        token=create_token(),
        user_id=user.id,
        created_at=utcnow(),
        expires_at=utcnow() + timedelta(days=_TOKEN_TTL_DAYS),
    )
    db.add(token)
    db.commit()
    return TokenResponse(token=token.token, user=_to_out(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return _to_out(user)


@router.post("/logout", status_code=204)
def logout(token: AuthToken = Depends(get_current_token), db: Session = Depends(get_db)):
    db.delete(token)
    db.commit()
    return None


@router.post("/change-password", response_model=UserOut)
def change_password(
    payload: ChangePasswordRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    token: AuthToken = Depends(get_current_token),
):
    if not verify_password(payload.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="原密码错误")
    if len(payload.new_password) < 8:
        raise HTTPException(status_code=400, detail="新密码长度至少 8 位")
    user.password_hash = hash_password(payload.new_password)
    user.must_change_password = False
    # 使该用户其他登录态全部失效，仅保留当前 token
    for other in db.scalars(select(AuthToken).where(AuthToken.user_id == user.id, AuthToken.id != token.id)).all():
        db.delete(other)
    db.commit()
    return _to_out(user)


@router.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    return [_to_out(u) for u in db.scalars(select(User).order_by(User.id)).all()]


@router.post("/users", response_model=UserOut)
def create_user(payload: CreateUserRequest, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    if db.scalar(select(User).where(User.username == payload.username)):
        raise HTTPException(status_code=409, detail="用户名已存在")
    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        role=payload.role,
        created_at=utcnow(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _to_out(user)
