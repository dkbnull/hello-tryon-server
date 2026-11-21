"""应用配置：从环境变量读取，提供开发默认值"""
import os

# 数据库：默认 SQLite，公网部署时通过 DATABASE_URL 切换 PostgreSQL
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./hello_tryon.db")

# JWT：默认开发密钥（重启登录态不失效）；生产必须通过环境变量注入强随机值
JWT_SECRET = os.getenv("JWT_SECRET", "dev-only-secret-change-me-in-production")
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "72"))

# 注册邀请码（生产通过环境变量替换）
INVITE_CODE = os.getenv("INVITE_CODE", "TRYON2026")

# 图片存储目录（磁盘起步，预留云 OSS）
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
ITEM_DIR = os.path.join(UPLOAD_DIR, "items")

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 单张 ≤ 10MB
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png"}
IMAGE_MAX_EDGE = 800  # 抠图后长边上限

# AI 模型存储目录（项目内，通过 U2NET_HOME 环境变量告知 rembg）
MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")

# 分类枚举（与 PRD 通用规则一致，全局唯一）
CATEGORIES = ("top", "bottom", "hat", "headwear", "scarf", "jewel")
CATEGORY_NAMES = {
    "top": "上衣", "bottom": "下衣", "hat": "帽子",
    "headwear": "头饰", "scarf": "围巾", "jewel": "首饰",
}

CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
