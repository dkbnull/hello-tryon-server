"""数据模型：用户、衣物、搭配记录"""
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


def utcnow():
    """当前 UTC 时间，作为各表 created_at / deletion_at 的统一时区基准"""
    return datetime.now(timezone.utc)


class User(Base):
    """用户表：注册账号与个人偏好"""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)  # 主键，自增用户 ID
    nickname: Mapped[str] = mapped_column(String(20))  # 昵称，不超过 20 字符
    account: Mapped[str] = mapped_column(String(64), unique=True, index=True)  # 登录账号（手机号或邮箱），全局唯一
    password_hash: Mapped[str] = mapped_column(String(128))  # 密码哈希（PBKDF2 单向加密，不存明文）
    avatar_gender: Mapped[str] = mapped_column(String(8), default="female")  # 虚拟人物性别：female=甜甜 / male=空空
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)  # 注册时间（UTC）
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)  # 信息更新时间（UTC），昵称/性别/密码/注销状态变更时手动刷新
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)  # 上次登录时间（UTC），登录成功或刷新令牌时更新
    deletion_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)  # 注销冷静期截止时间；NULL=未申请注销，期间登录自动取消注销


class ClothingItem(Base):
    """衣物表：用户衣橱内的单品"""
    __tablename__ = "clothing_items"

    id: Mapped[int] = mapped_column(primary_key=True)  # 主键，自增衣物 ID
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)  # 所属用户 ID，外键关联 users.id
    name: Mapped[str] = mapped_column(String(20))  # 衣物名称，留空时自动命名为「分类名-序号」
    category: Mapped[str] = mapped_column(String(16), index=True)  # 分类：top/bottom/hat/headwear/scarf/jewel
    image: Mapped[str] = mapped_column(String(128))  # 图片文件名，相对 ITEM_DIR，静态访问路径为 /static/items/{image}
    source: Mapped[str] = mapped_column(String(8), default="AI")  # 图片来源：AI=AI 抠图 / manual=手动上传
    conf_cut: Mapped[float] = mapped_column(Float, default=0.0)  # AI 抠图置信度（0~1，低于 0.6 视为手动）
    conf_cls: Mapped[float] = mapped_column(Float, default=0.0)  # AI 分类置信度（0~1，0.5=用户在结果页手动确认）
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)  # 入库时间（UTC），衣橱列表按此倒序排列
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)  # 信息更新时间（UTC），衣物名称/分类变更时手动刷新


class OutfitRecord(Base):
    """搭配记录表：一次保存 = 一条记录，同一天可存多条"""
    __tablename__ = "outfit_records"

    id: Mapped[int] = mapped_column(primary_key=True)  # 主键，自增记录 ID
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)  # 所属用户 ID，外键关联 users.id
    worn_date: Mapped[str] = mapped_column(String(10), index=True)  # 搭配日期（YYYY-MM-DD），前端按用户本地日期提交，作为日历索引
    gender: Mapped[str] = mapped_column(String(8))  # 保存时的人物性别：female=甜甜 / male=空空，回放渲染必需
    items: Mapped[dict] = mapped_column(JSON)  # 六部位穿着快照：top/bottom/hat/headwear/scarf 为衣物 id 或 null，jewel 为 id 列表
    adjustments: Mapped[dict] = mapped_column(JSON)  # 各衣物的手动调整快照：衣物 id → {dx, dy, scale}
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)  # 保存时间（UTC），当日列表按此倒序
