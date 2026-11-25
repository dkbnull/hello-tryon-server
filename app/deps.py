"""FastAPI 依赖：数据库会话 + 当前登录用户"""
from fastapi import Depends, Request
from sqlalchemy.orm import Session

from .database import get_db
from .errors import ApiError
from .models import User
from .security import decode_token


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise ApiError(401, "NO_TOKEN", "未登录")
    user_id = decode_token(auth.removeprefix("Bearer ").strip())
    if user_id is None:
        raise ApiError(401, "TOKEN_INVALID", "登录态已失效，请重新登录")
    user = db.get(User, user_id)
    if user is None:
        raise ApiError(401, "ACCOUNT_NOT_FOUND", "账号不存在")
    return user
