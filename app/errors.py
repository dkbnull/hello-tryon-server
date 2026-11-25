"""统一错误响应：所有错误输出 {code, message} 结构（非 2xx 状态码）"""
from fastapi import HTTPException


class ApiError(HTTPException):
    """业务错误：携带稳定错误码，由全局处理器输出 {code, message}"""

    def __init__(self, status_code: int, code: str, message: str):
        super().__init__(status_code=status_code, detail={"code": code, "message": message})


# 未显式指定错误码的 HTTPException，按状态码给默认错误码
DEFAULT_CODES = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
}


def error_body(status_code: int, detail: object) -> dict:
    """把 HTTPException.detail 规整为 {code, message}"""
    if isinstance(detail, dict) and "code" in detail:
        return detail
    return {
        "code": DEFAULT_CODES.get(status_code, f"E{status_code}"),
        "message": str(detail),
    }
