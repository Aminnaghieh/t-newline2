"""
chat.py – Main chat/agent API endpoint.
"""

from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Optional
from backend.services.agent import process_message

router = APIRouter(prefix="/api", tags=["chat"])


class ChatRequest(BaseModel):
    message: str = ""
    lat: Optional[float] = None
    lon: Optional[float] = None
    session_id: Optional[str] = ""
    context: Optional[dict] = None


@router.post("/chat")
async def chat(req: ChatRequest):
    """Main chat endpoint – processes user messages and returns structured responses."""
    result = process_message(
        message=req.message,
        session_id=req.session_id or "",
        lat=req.lat,
        lon=req.lon,
        context=req.context,
    )
    return result
