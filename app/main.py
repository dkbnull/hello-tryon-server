"""HelloTryon 后端入口"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import CORS_ORIGINS, ITEM_DIR, UPLOAD_DIR
from .database import SessionLocal, init_db
from .errors import error_body
from .routers import auth, items, outfits


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    db = SessionLocal()
    try:
        auth.purge_overdue_deletions(db)  # 启动时清理冷静期已结束的注销账号
    finally:
        db.close()
    yield


app = FastAPI(title="HelloTryon API", version="0.1.0", lifespan=lifespan)


@app.exception_handler(HTTPException)
async def http_error_handler(_, exc: HTTPException):
    """统一错误体：{code, message}"""
    return JSONResponse(status_code=exc.status_code, content=error_body(exc.status_code, exc.detail))


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_, exc: RequestValidationError):
    """Pydantic 参数校验失败：取第一条错误信息返回给前端展示"""
    first = exc.errors()[0]["msg"] if exc.errors() else "参数校验失败"
    return JSONResponse(
        status_code=422,
        content={"code": "VALIDATION_ERROR", "message": f"参数错误：{first}"},
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(items.router)
app.include_router(outfits.router)

# 图片静态托管（磁盘目录起步，预留云 OSS）
os.makedirs(ITEM_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=UPLOAD_DIR), name="static")


@app.get("/api/health")
def health():
    return {"status": "ok"}
