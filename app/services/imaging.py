"""图像处理：AI 抠图（rembg 可选）+ EXIF 摆正 + 衣架裁剪 + 裁剪缩放 + 自动分类占位"""
import io
import os
import secrets

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

from ..config import IMAGE_MAX_EDGE, MODELS_DIR

# 模型下载/缓存到项目内 models/ 目录，避免写入用户目录 ~/.rembg
# rembg 约定：U2NET_HOME 作为平铺根目录，模型文件直接位于其下（models/u2net.onnx）
os.environ.setdefault("U2NET_HOME", MODELS_DIR)

try:
    from rembg import remove, new_session

    # 指定 u2net 模型（176MB，衣物/通用抠图效果好且比新版默认的 bria-rmbg 1GB 小）
    _rembg_session = new_session("u2net")
    REMBG_AVAILABLE = True
except Exception:  # ImportError 或模型加载失败
    REMBG_AVAILABLE = False


def process_image(raw: bytes) -> tuple[bytes, float]:
    """处理上传图片，返回 (透明底 PNG 字节, 抠图置信度)。

    rembg 可用时执行 AI 抠图；不可用时降级为原图转 PNG（保留原样），
    置信度降低以提示用户人工核对。
    """
    try:
        img = Image.open(io.BytesIO(raw))
        # 手机拍摄的照片常带 EXIF 方向标记，按标记转正
        img = ImageOps.exif_transpose(img)
        img.load()
    except (UnidentifiedImageError, OSError) as e:
        raise ValueError("无法解析图片文件") from e

    # 抠图前先压到目标长边：u2net 推理与后处理均按输入分辨率分配内存，
    # 全尺寸原图峰值可达数百 MB，缩小后内存峰值即降至最终产物量级
    img.thumbnail((IMAGE_MAX_EDGE, IMAGE_MAX_EDGE), Image.LANCZOS)

    if REMBG_AVAILABLE:
        try:
            result = remove(img.convert("RGBA"), session=_rembg_session)
            conf = 0.92
        except Exception:
            result, conf = img.convert("RGBA"), 0.5
    else:
        result, conf = img.convert("RGBA"), 0.5

    result = _trim_and_scale(result)
    result = _straighten(result)
    result = _remove_hanger(result)
    buf = io.BytesIO()
    result.save(buf, format="PNG")
    return buf.getvalue(), conf


def _trim_and_scale(img: Image.Image) -> Image.Image:
    """裁掉四周透明区域并限制长边尺寸"""
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)

    w, h = img.size
    scale = min(1.0, IMAGE_MAX_EDGE / max(w, h))
    if scale < 1.0:
        img = img.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.LANCZOS)
    return img


def _straighten(img: Image.Image) -> Image.Image:
    """摆正明显歪斜的衣物照片（挂拍歪斜）。

    判据：取轮廓中部 1/3 行（避开顶部肩角与底部摆，那里边缘由角点主导），
    拟合左右边缘斜率。真歪斜时左右边缘斜率同号且大小相近；
    形状不对称（L 形裤腿、A 字裙摆）左右斜率不同号或差异大，不会误转。
    仅纠正 3°~25° 的倾斜，宁可不转不误转。
    """
    alpha = np.asarray(img)[:, :, 3]
    h, w = alpha.shape
    widths = (alpha > 128).sum(axis=1)
    rows = np.where(widths > widths.max() * 0.3)[0]  # 排除顶部钩等细结构行
    if len(rows) < 50:
        return img

    # 中部 1/3 行
    lo, hi = rows[0] + (rows[-1] - rows[0]) // 3, rows[0] + 2 * (rows[-1] - rows[0]) // 3
    mid = rows[(rows >= lo) & (rows <= hi)]
    if len(mid) < 20:
        return img

    ls = np.polyfit(mid, [np.where(alpha[y] > 128)[0][0] for y in mid], 1)[0]
    rs = np.polyfit(mid, [np.where(alpha[y] > 128)[0][-1] for y in mid], 1)[0]

    # 左右边缘斜率同号（对称展开/形状突变即放弃），角度差过大视为形状干扰
    if ls * rs <= 0:
        return img
    a_l, a_r = float(np.degrees(np.arctan(ls))), float(np.degrees(np.arctan(rs)))
    if abs(a_l - a_r) > 8:
        return img

    # 取倾斜更明显的一侧（更接近平直边缘的真实倾角）
    angle = a_l if abs(a_l) > abs(a_r) else a_r
    if abs(angle) < 3:  # 倾角 <3° 不动
        return img
    if abs(angle) > 25:
        return img
    return img.rotate(-angle, resample=Image.BICUBIC, expand=True, fillcolor=(0, 0, 0, 0))


def _remove_hanger(img: Image.Image) -> Image.Image:
    """清除挂拍衣物中的衣架：裁掉顶部突出的衣架钩，并抹除横穿领口的衣架横杆。

    钩：顶部细长窄条，通过逐行宽度分析裁剪。
    横杆：左右贯通的实心细条，上下邻行是领口 V 形分离区；将其 alpha 清零，
    条纹衣物不会误伤（条纹上下均为不透明衣身，不满足"邻行分离"条件）。
    """
    img = _crop_top_hanger(img)
    img = _clear_hanger_bar(img)
    bbox = img.getbbox()
    if bbox and bbox != (0, 0, img.width, img.height):
        img = img.crop(bbox)
    return img


def _row_runs(row: np.ndarray) -> list[np.ndarray]:
    """返回一行中连续 True 段的索引数组列表"""
    idx = np.where(row)[0]
    if len(idx) == 0:
        return []
    return np.split(idx, np.where(np.diff(idx) > 1)[0] + 1)


def _crop_top_hanger(img: Image.Image) -> Image.Image:
    """裁掉顶部突出的衣架钩：从顶部向下找第一段连续的宽行（衣服主体）"""
    alpha = np.asarray(img)[:, :, 3]
    h, w = alpha.shape
    widths = (alpha > 128).sum(axis=1)
    if widths.max() == 0 or widths[0] >= widths.max() * 0.4:
        return img  # 顶部即主体（平铺衣物），无需处理

    big = widths >= widths.max() * 0.4
    min_body = max(3, int(h * 0.03))  # 连续 ≥3% 高度的宽行段才视为衣服主体
    top, run = 0, 0
    for y in range(h):
        if big[y]:
            run += 1
            if run >= min_body:
                top = y - run + 1  # 主体起始行（跳过钩与孤立横杆）
                break
        else:
            run = 0

    if 0 < top <= h * 0.15:
        img = img.crop((0, top, w, h))
    return img


def _clear_hanger_bar(img: Image.Image) -> Image.Image:
    """抹除横穿领口的衣架横杆：贯通实心细条 + 上下邻行为领口分离区"""
    arr = np.asarray(img).copy()
    alpha = arr[:, :, 3]
    h, w = alpha.shape
    widths = (alpha > 128).sum(axis=1)
    max_w = widths.max()
    if max_w == 0:
        return img

    def seg_ratio(y: int) -> float:
        """该行最长连续段占行内不透明像素的比例（贯通≈1，分离<0.6）"""
        row = alpha[y] > 128
        n = int(row.sum())
        return max((len(s) for s in _row_runs(row)), default=0) / n if n else 0.0

    # 横杆只可能出现在上部 45% 区域内
    solid = np.array([seg_ratio(y) > 0.8 for y in range(int(h * 0.45))])
    min_bar = 2  # 至少连续 2 行贯通才算横杆厚度
    for y0 in range(len(solid) - min_bar + 1):
        if not solid[y0]:
            continue
        y1 = y0
        while y1 + 1 < len(solid) and solid[y1 + 1]:
            y1 += 1
        thick = y1 - y0 + 1
        if thick > max(4, int(h * 0.02)):
            continue  # 太厚是衣身
        # 任一邻行是分离区（领口开口）即判定为横杆
        neighbors = [
            seg_ratio(yy) for yy in (y0 - 1, y1 + 1)
            if 0 <= yy < h and (alpha[yy] > 128).sum() > 0
        ]
        if neighbors and max(neighbors) < 0.6:
            arr[y0 : y1 + 1, :, 3] = 0
    return Image.fromarray(arr, "RGBA")


def auto_classify(raw: bytes) -> tuple[str, float]:
    """自动分类占位：一期以用户选择/默认分类为主。

    后续接入真实分类模型时替换此实现。
    """
    return "top", 0.5


def rotate_processed(png: bytes, rotation: int) -> bytes:
    """入库前按用户手动旋转角度处理抠图结果（rotation 为顺时针角度）"""
    img = Image.open(io.BytesIO(png)).convert("RGBA")
    if rotation % 360:
        # PIL rotate 正角为逆时针，取负实现顺时针
        img = img.rotate(-rotation, expand=True, resample=Image.BICUBIC, fillcolor=(0, 0, 0, 0))
        bbox = img.getbbox()
        if bbox:
            img = img.crop(bbox)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def new_image_filename() -> str:
    return f"{secrets.token_hex(12)}.png"
