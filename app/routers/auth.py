"""注册 / 登录 / 用户信息"""
import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..config import INVITE_CODE

from ..database import get_db
from ..deps import get_current_user
from ..models import User
from ..schemas import (
    LoginIn, PasswordChangeIn, RefreshIn, RegisterIn,
    TokenOut, TokenRefreshOut, UserMeIn, UserOut,
)
from ..security import (
    check_password_strength, create_token, decode_token, hash_password, verify_password,
)


def _issue_tokens(user_id: int) -> TokenRefreshOut:
    return TokenRefreshOut(
        token=create_token(user_id),
        refresh_token=create_token(user_id, "refresh"),
    )

router = APIRouter(prefix="/api/auth", tags=["auth"])

_EMAIL_RE = re.compile(r"^\S+@\S+\.\S+$")
_PHONE_RE = re.compile(r"^1\d{10}$")


@router.post("/register", response_model=TokenOut)
def register(data: RegisterIn, db: Session = Depends(get_db)):
    if data.invite_code.strip() != INVITE_CODE:
        raise HTTPException(403, "邀请码无效，无法注册")
    account = data.account.strip().lower()
    if not (_EMAIL_RE.match(account) or _PHONE_RE.match(account)):
        raise HTTPException(400, "请输入正确的邮箱或手机号")
    if not check_password_strength(data.password):
        raise HTTPException(400, "密码至少 8 位，且大写字母、小写字母、数字、特殊字符中至少包含 3 类")
    if db.query(User).filter(User.account == account).first():
        raise HTTPException(400, "该账号已注册，请直接登录")

    user = User(
        nickname=data.nickname.strip(),
        account=account,
        password_hash=hash_password(data.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return TokenOut(**_issue_tokens(user.id).model_dump(), user=UserOut.model_validate(user))


@router.post("/login", response_model=TokenOut)
def login(data: LoginIn, db: Session = Depends(get_db)):
    account = data.account.strip().lower()
    user = db.query(User).filter(User.account == account).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "账号或密码错误")
    return TokenOut(**_issue_tokens(user.id).model_dump(), user=UserOut.model_validate(user))


@router.post("/refresh", response_model=TokenRefreshOut)
def refresh(data: RefreshIn, db: Session = Depends(get_db)):
    """刷新令牌轮换：校验 refresh_token，签发新的 access + refresh"""
    user_id = decode_token(data.refresh_token, typ="refresh")
    if user_id is None:
        raise HTTPException(401, "登录态已失效，请重新登录")
    if db.get(User, user_id) is None:
        raise HTTPException(401, "账号不存在")
    return TokenRefreshOut(
        token=create_token(user_id),
        refresh_token=create_token(user_id, "refresh"),
    )


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return UserOut.model_validate(user)


@router.patch("/me", response_model=UserOut)
def update_me(data: UserMeIn, user: User = Depends(get_current_user),
              db: Session = Depends(get_db)):
    if data.nickname is not None:
        user.nickname = data.nickname.strip()
    if data.avatar_gender is not None:
        if data.avatar_gender not in ("female", "male"):
            raise HTTPException(400, "人物性别仅支持 female / male")
        user.avatar_gender = data.avatar_gender
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)


@router.patch("/me/password", response_model=UserOut)
def change_password(data: PasswordChangeIn, user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    if not verify_password(data.old_password, user.password_hash):
        raise HTTPException(400, "当前密码不正确")
    if not check_password_strength(data.new_password):
        raise HTTPException(400, "新密码至少 8 位，且大写字母、小写字母、数字、特殊字符中至少包含 3 类")
    if data.old_password == data.new_password:
        raise HTTPException(400, "新密码不能与当前密码相同")
    user.password_hash = hash_password(data.new_password)
    db.commit()
    return UserOut.model_validate(user)
