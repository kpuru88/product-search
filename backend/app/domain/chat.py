"""Chat domain models."""
from pydantic import BaseModel
from typing import Optional
from app.domain.intent import SearchIntent


class ChatRequest(BaseModel):
    """Request for chat endpoints."""
    message: str


class ChatIntakeResponse(BaseModel):
    """Response from chat intake with parsed intent."""
    intent: SearchIntent
    clarification: Optional[str] = None

