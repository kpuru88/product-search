"""Chat intake API endpoints."""
from fastapi import APIRouter, HTTPException
from app.domain.chat import ChatRequest, ChatIntakeResponse
from app.api.deps import get_chat_intake_service

router = APIRouter()


@router.post("/api/chat/intake", response_model=ChatIntakeResponse)
async def chat_intake(request: ChatRequest):
    """
    Process a chat intake request and extract structured search intent.
    
    Args:
        request: Chat request with user message
        
    Returns:
        ChatIntakeResponse with parsed intent
        
    Raises:
        HTTPException: If processing fails
    """
    try:
        service = get_chat_intake_service()
        return await service.process_intake(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat intake failed: {str(e)}")

