"""对话接口：SSE 流式输出，事件序列 chunk* → done | error。"""
from __future__ import annotations

import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from ..core.errors import AppError, error_payload
from ..schemas.chat import ChatDonePayload, ChatRequest
from ..services import agent

router = APIRouter(prefix="/chat", tags=["chat"])


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def _chunks(text: str):
    """把回复切成小块，模拟流式输出。"""
    step = max(6, len(text) // 6)
    for i in range(0, len(text), step):
        yield text[i : i + step]


@router.post("")
async def chat(req: ChatRequest) -> StreamingResponse:
    async def gen():
        try:
            result = agent.handle(req.message, req.session_id)
            sid = result.get("session_id")

            # 流式输出回复文本
            reply = result.get("reply", "")
            for piece in _chunks(reply):
                yield _sse({"type": "chunk", "content": piece, "session_id": sid})

            # 完成事件
            payload: dict = {"type": result.get("type", "reply"), "reply": reply}
            if result.get("plan"):
                payload["plan"] = result["plan"].model_dump()
            if result.get("missing"):
                payload["missing"] = result["missing"]
            yield _sse({"type": "done", "session_id": sid, "payload": payload})
        except AppError as e:
            yield _sse({"type": "error", "error": {"code": e.code, "message": e.message}})
        except Exception:
            # 统一兜底：不向用户暴露堆栈
            yield _sse(
                {"type": "error", "error": {"code": "internal_error", "message": "服务暂时不可用，请稍后重试"}}
            )

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
