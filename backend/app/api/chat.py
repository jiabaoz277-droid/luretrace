"""对话接口：SSE 流式输出，事件序列 chunk* → done | error。

方案类回复走真实模型逐 token 流式；追问/知识类短文本走模板分块。
流中途失败会以 error 事件返回统一结构，不静默断流。
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from ..core.auth import current_user_id
from ..core.errors import AppError
from ..schemas.chat import ChatRequest
from ..services import agent, llm

router = APIRouter(prefix="/chat", tags=["chat"])


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def _chunks(text: str):
    """把短文本切成小块输出。"""
    step = max(6, len(text) // 6)
    for i in range(0, len(text), step):
        yield text[i : i + step]


@router.post("")
async def chat(req: ChatRequest, request: Request) -> StreamingResponse:
    user_id = current_user_id(request)

    async def gen():
        try:
            result = agent.prepare(
                req.message, req.session_id, context=req.context, user_id=user_id
            )
            sid = result.get("session_id")
            reply_parts: list[str] = []

            if result.get("plan"):
                # 真实模型逐 token 流式（安全 no_go 时为确定性文案）
                for piece in llm.stream_reply(result["plan"]):
                    reply_parts.append(piece)
                    yield _sse({"type": "chunk", "content": piece, "session_id": sid})
            else:
                text = result.get("reply") or ""
                reply_parts.append(text)
                for piece in _chunks(text):
                    yield _sse({"type": "chunk", "content": piece, "session_id": sid})

            reply = "".join(reply_parts)
            if not reply and result.get("plan"):
                reply = "已为你生成方案，详见下方方案卡。"

            payload: dict = {"type": result.get("type", "reply"), "reply": reply}
            if result.get("plan"):
                payload["plan"] = result["plan"].model_dump()
            if result.get("missing"):
                payload["missing"] = result["missing"]
            if result.get("steps"):
                payload["steps"] = result["steps"]
            if result.get("report"):
                payload["report"] = result["report"]
            if result.get("quick_options"):
                payload["quick_options"] = result["quick_options"]
            if result.get("spots"):
                payload["spots"] = result["spots"]
            if result.get("insight"):
                payload["insight"] = result["insight"]
            yield _sse({"type": "done", "session_id": sid, "payload": payload})
        except AppError as e:
            yield _sse({"type": "error", "error": {"code": e.code, "message": e.message}})
        except Exception:
            # 统一兜底：不向用户暴露堆栈
            yield _sse(
                {
                    "type": "error",
                    "error": {"code": "internal_error", "message": "服务暂时不可用，请稍后重试"},
                }
            )

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
