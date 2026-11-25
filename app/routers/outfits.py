"""搭配记录：保存快照、按月查询、详情、删除"""
import re

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..config import CATEGORIES
from ..database import get_db
from ..deps import get_current_user
from ..errors import ApiError
from ..models import OutfitRecord, User
from ..schemas import OutfitIn, OutfitOut

router = APIRouter(prefix="/api/outfits", tags=["outfits"])

JEWEL_LIMIT = 3  # 与一期首饰同穿上限一致
MONTH_RE = re.compile(r"^\d{4}-\d{2}$")
SINGLE_SLOTS = ("top", "bottom", "hat", "headwear", "scarf")


def _validate_items(items: dict) -> None:
    """校验穿着快照结构：单件部位为衣物 id 或 null，首饰为 id 列表且不超上限"""
    if not isinstance(items, dict):
        raise ApiError(400, "SNAPSHOT_INVALID", "items 必须为对象")
    for k in items:
        if k not in CATEGORIES:
            raise ApiError(400, "SLOT_INVALID", f"无效的部位：{k}")
    for k in SINGLE_SLOTS:
        v = items.get(k)
        if v is not None and not isinstance(v, int):
            raise ApiError(400, "SLOT_INVALID", f"部位 {k} 的值必须为衣物 id 或 null")
    jewel = items.get("jewel", [])
    if not isinstance(jewel, list) or not all(isinstance(x, int) for x in jewel):
        raise ApiError(400, "JEWEL_INVALID", "jewel 必须为衣物 id 列表")
    if len(jewel) > JEWEL_LIMIT:
        raise ApiError(400, "JEWEL_LIMIT_EXCEEDED", f"首饰同穿上限 {JEWEL_LIMIT} 件")


def _validate_adjustments(adj: dict) -> None:
    """校验调整快照结构：衣物 id → {dx, dy, scale, z?} 数值字段（z 为图层序，可选）"""
    if not isinstance(adj, dict):
        raise ApiError(400, "ADJUST_INVALID", "adjustments 必须为对象")
    for k, v in adj.items():
        if not isinstance(v, dict) or not all(
            isinstance(v.get(f), (int, float)) for f in ("dx", "dy", "scale")
        ):
            raise ApiError(400, "ADJUST_INVALID", f"adjustments[{k}] 必须包含数值的 dx/dy/scale")
        if "z" in v and not isinstance(v["z"], (int, float)):
            raise ApiError(400, "ADJUST_INVALID", f"adjustments[{k}].z 必须为数值")


@router.post("", response_model=OutfitOut)
def save_outfit(data: OutfitIn, user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    """保存当前搭配快照（一次保存一条记录，不做覆盖）"""
    if data.gender not in ("female", "male"):
        raise ApiError(400, "GENDER_INVALID", "无效的人物性别")
    _validate_items(data.items)
    _validate_adjustments(data.adjustments)

    record = OutfitRecord(
        user_id=user.id,
        worn_date=data.worn_date,
        gender=data.gender,
        items=data.items,
        adjustments=data.adjustments,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("", response_model=list[OutfitOut])
def list_outfits(month: str, user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    """按月查询记录（worn_date 前缀匹配），供月历标记与当日列表"""
    if not MONTH_RE.match(month):
        raise ApiError(400, "MONTH_INVALID", "month 必须为 YYYY-MM 格式")
    records = (
        db.query(OutfitRecord)
        .filter(OutfitRecord.user_id == user.id, OutfitRecord.worn_date.like(f"{month}%"))
        .order_by(OutfitRecord.worn_date.desc(), OutfitRecord.created_at.desc())
        .all()
    )
    return records


@router.get("/{record_id}", response_model=OutfitOut)
def get_outfit(record_id: int, user: User = Depends(get_current_user),
               db: Session = Depends(get_db)):
    record = db.get(OutfitRecord, record_id)
    if not record or record.user_id != user.id:
        raise ApiError(404, "OUTFIT_NOT_FOUND", "搭配记录不存在")
    return record


@router.delete("/{record_id}")
def delete_outfit(record_id: int, user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    record = db.get(OutfitRecord, record_id)
    if not record or record.user_id != user.id:
        raise ApiError(404, "OUTFIT_NOT_FOUND", "搭配记录不存在")
    db.delete(record)
    db.commit()
    return {"ok": True}
