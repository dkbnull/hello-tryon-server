"""数据模型：用户、衣物"""
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


def utcnow():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    nickname: Mapped[str] = mapped_column(String(20))
    account: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(128))
    avatar_gender: Mapped[str] = mapped_column(String(8), default="female")  # female/male
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ClothingItem(Base):
    __tablename__ = "clothing_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(20))
    category: Mapped[str] = mapped_column(String(16), index=True)
    image: Mapped[str] = mapped_column(String(128))  # 相对 ITEM_DIR 的文件名
    source: Mapped[str] = mapped_column(String(8), default="AI")  # AI=AI抠图 / manual=手动
    conf_cut: Mapped[float] = mapped_column(Float, default=0.0)  # 抠图置信度
    conf_cls: Mapped[float] = mapped_column(Float, default=0.0)  # 分类置信度
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
