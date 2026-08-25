"""统一错误结构：{"error": {"code", "message"}}，不向用户暴露堆栈。"""


class AppError(Exception):
    """业务错误，code 为机器可读的错误码。"""

    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def error_payload(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message}}
