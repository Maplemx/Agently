import asyncio
from typing import AsyncGenerator

from fastapi import APIRouter, WebSocket
from fastapi.responses import StreamingResponse

from .flow import build_flow
from .schemas import AskRequest, AskResponse

router = APIRouter()

flow = build_flow()


@router.get("/sse")
async def sse(question: str):
    async def event_stream() -> AsyncGenerator[str, None]:
        for event in flow.get_runtime_stream({"question": question}, timeout=None):
            yield f"data: {event}\n\n"
            await asyncio.sleep(0)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    while True:
        question = await ws.receive_text()
        for event in flow.get_runtime_stream({"question": question}, timeout=None):
            await ws.send_text(str(event))
            await asyncio.sleep(0)


@router.post("/ask", response_model=AskResponse)
async def ask(body: AskRequest):
    result = flow.start({"question": body.question})
    reply = result.get("reply") if isinstance(result, dict) else str(result)
    return AskResponse(reply=str(reply))
