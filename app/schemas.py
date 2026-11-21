"""请求/响应 Pydantic 模型"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RegisterIn(BaseModel):
    nickname: str = Field(min_length=1, max_length=20)
    account: str = Field(min_length=1, max_length=64)  # 邮箱或手机号
    password: str = Field(min_length=8, max_length=64)
    invite_code: str = Field(min_length=1, max_length=32)


class LoginIn(BaseModel):
    account: str
    password: str


class UserMeIn(BaseModel):
    nickname: str | None = Field(default=None, min_length=1, max_length=20)
    avatar_gender: str | None = None  # female / male


class PasswordChangeIn(BaseModel):
    old_password: str = Field(min_length=1, max_length=64)
    new_password: str = Field(min_length=8, max_length=64)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nickname: str
    account: str
    avatar_gender: str
    created_at: datetime


class TokenOut(BaseModel):
    token: str
    user: UserOut


class ItemPatchIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=20)
    category: str | None = None


class ItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    category: str
    image: str  # 静态访问路径
    source: str
    conf_cut: float
    conf_cls: float
    created_at: datetime
