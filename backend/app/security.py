import hashlib
import hmac
import secrets

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AuthToken, User, utcnow

_PBKDF2_ITERATIONS = 200_000


def hash_password(password: str) -> str:
    """PBKDF2-HMAC-SHA256，随机 salt，存储格式 salt_hex$hash_hex。"""
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS)
    return f"{salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, hash_hex = stored.split("$", 1)
        salt = bytes.fromhex(salt_hex)
    except ValueError:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS)
    return hmac.compare_digest(digest.hex(), hash_hex)


def create_token() -> str:
    return secrets.token_hex(32)


def get_current_token(request: Request, db: Session = Depends(get_db)) -> AuthToken:
    """解析 Authorization: Bearer <token>，无效或过期抛 401。"""
    auth = request.headers.get("Authorization", "")
    token = auth[7:].strip() if auth.startswith("Bearer ") else ""
    record = db.scalar(select(AuthToken).where(AuthToken.token == token)) if token else None
    if record is None or (record.expires_at is not None and record.expires_at <= utcnow()):
        raise HTTPException(status_code=401, detail="未认证或登录已过期")
    return record


def get_current_user(token: AuthToken = Depends(get_current_token), db: Session = Depends(get_db)) -> User:
    user = db.get(User, token.user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="未认证或登录已过期")
    return user


def require_roles(*roles: str):
    """角色守卫工厂：当前用户角色不在允许列表内抛 403。"""

    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="权限不足")
        return user

    return checker
