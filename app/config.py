"""应用配置：优先读取环境变量，本地开发自动加载项目根目录 .env"""
import os

from dotenv import load_dotenv

# 不覆盖已注入的环境变量（Docker/服务器环境优先），仅本地开发生效
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

# 数据库：默认 SQLite，公网部署时通过 DATABASE_URL 切换 PostgreSQL
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./hello_tryon.db")

# JWT：默认开发密钥（重启登录态不失效）；生产必须通过环境变量注入强随机值
JWT_SECRET = os.getenv("JWT_SECRET", "dev-only-secret-change-me-in-production")
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "2"))  # 访问令牌有效期
JWT_REFRESH_DAYS = int(os.getenv("JWT_REFRESH_DAYS", "30"))  # 刷新令牌有效期

# 账号注销冷静期（天），期间登录自动取消注销
ACCOUNT_DELETION_DAYS = int(os.getenv("ACCOUNT_DELETION_DAYS", "7"))

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
