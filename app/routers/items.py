"""衣橱衣物：上传（AI 处理）、浏览、编辑、删除"""
import base64
import os

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..config import ALLOWED_CONTENT_TYPES, CATEGORY_NAMES, CATEGORIES, ITEM_DIR, MAX_UPLOAD_BYTES
from ..database import get_db
from ..deps import get_current_user
from ..models import ClothingItem, User
from ..schemas import ItemOut, ItemPatchIn
from ..services import imaging

router = APIRouter(prefix="/api/items", tags=["items"])


def _item_out(item: ClothingItem) -> ItemOut:
    out = ItemOut.model_validate(item)
    out.image = f"/static/items/{item.image}"
    return out


def _auto_name(db: Session, user_id: int, category: str) -> str:
    """留空时自动命名：「分类名-序号」，序号为该分类现有件数 +1"""
    count = (
        db.query(ClothingItem)
        .filter(ClothingItem.user_id == user_id, ClothingItem.category == category)
        .count()
    )
    return f"{CATEGORY_NAMES[category]}-{count + 1:02d}"


def _read_upload(file: UploadFile, allowed: set[str] = ALLOWED_CONTENT_TYPES,
                 msg: str = "仅支持 JPG / PNG 格式图片") -> bytes:
    """上传约束：格式白名单、≤10MB"""
    if file.content_type not in allowed:
        raise HTTPException(400, msg)
    raw = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(400, "图片大小不能超过 10MB")
    return raw


@router.post("/process")
def process_photo(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    """第一步：AI 处理（抠图/摆正/去衣架），结果不落库，等待用户确认"""
    raw = _read_upload(file)
    try:
        processed, cut_conf = imaging.process_image(raw)
    except ValueError as e:
        raise HTTPException(400, str(e))
    category, _ = imaging.auto_classify(raw)
    return {
        "image": base64.b64encode(processed).decode(),
        "category": category,
        "conf": cut_conf,
    }


@router.post("", response_model=ItemOut)
def upload_item(
    image: UploadFile = File(...),  # 已处理 PNG（第一步返回的抠图结果）
    rotation: int = Form(0),  # 用户手动旋转角度（顺时针）
    category: str = Form(...),
    name: str = Form(""),
    conf: float = Form(0.92),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """第二步：确认入库（应用旋转、命名、分类后落库）"""
    raw = _read_upload(image, {"image/png"}, "入库图片必须为 PNG（AI 处理结果）")
    if category not in CATEGORIES:
        raise HTTPException(400, "无效的分类")

    try:
        processed = imaging.rotate_processed(raw, rotation)
    except ValueError as e:
        raise HTTPException(400, str(e))

    os.makedirs(ITEM_DIR, exist_ok=True)
    filename = imaging.new_image_filename()
    with open(os.path.join(ITEM_DIR, filename), "wb") as f:
        f.write(processed)

    item = ClothingItem(
        user_id=user.id,
        name=(name.strip() or _auto_name(db, user.id, category)),
        category=category,
        image=filename,
        source="manual" if conf < 0.6 else "AI",
        conf_cut=conf,
        conf_cls=0.5,  # 分类经用户在结果页确认
    )
    db.add(item)
    try:
        db.commit()
    except Exception:
        db.rollback()
        os.remove(os.path.join(ITEM_DIR, filename))  # 提交失败时清理已写盘文件，避免孤儿文件
        raise
    db.refresh(item)
    return _item_out(item)


@router.get("", response_model=list[ItemOut])
def list_items(category: str = "", user: User = Depends(get_current_user),
               db: Session = Depends(get_db)):
    q = db.query(ClothingItem).filter(ClothingItem.user_id == user.id)
    if category:
        if category not in CATEGORIES:
            raise HTTPException(400, "无效的分类")
        q = q.filter(ClothingItem.category == category)
    items = q.order_by(ClothingItem.created_at.desc()).all()
    return [_item_out(i) for i in items]


@router.patch("/{item_id}", response_model=ItemOut)
def update_item(item_id: int, data: ItemPatchIn,
                user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = db.get(ClothingItem, item_id)
    if not item or item.user_id != user.id:
        raise HTTPException(404, "衣物不存在")
    if data.name is not None:
        item.name = data.name.strip() or item.name
    if data.category is not None:
        if data.category not in CATEGORIES:
            raise HTTPException(400, "无效的分类")
        item.category = data.category
    db.commit()
    db.refresh(item)
    return _item_out(item)


@router.delete("/{item_id}")
def delete_item(item_id: int, user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    item = db.get(ClothingItem, item_id)
    if not item or item.user_id != user.id:
        raise HTTPException(404, "衣物不存在")
    db.delete(item)
    db.commit()
    try:
        os.remove(os.path.join(ITEM_DIR, item.image))
    except OSError:
        pass  # 文件缺失不影响删除结果
    return {"ok": True}
