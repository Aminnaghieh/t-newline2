"""
chat.py – Main chat/agent API endpoint.
Routed through the LLM-orchestrated agent with automatic rule-based
fallback; the response always carries both legacy `cards` and the new
validated `ui` blocks (see services/ui_schema.py).
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional
from backend.services.llm_agent import handle_chat

router = APIRouter(prefix="/api", tags=["chat"])


class ChatRequest(BaseModel):
    message: str = Field("", max_length=1000, description="User message text")
    lat: Optional[float] = Field(None, ge=-90.0, le=90.0, description="User latitude")
    lon: Optional[float] = Field(None, ge=-180.0, le=180.0, description="User longitude")
    session_id: Optional[str] = Field("", max_length=128, description="Client session ID")
    context: Optional[dict] = Field(None, description="Contextual actions")


@router.post("/chat")
async def chat(req: ChatRequest):
    """Main chat endpoint – processes user messages and returns structured responses."""
    result = handle_chat(
        message=req.message,
        session_id=req.session_id or "",
        lat=req.lat,
        lon=req.lon,
        context=req.context,
    )
    return result
