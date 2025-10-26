"""Product search API endpoints."""
from fastapi import APIRouter, HTTPException
from app.domain.chat import ChatRequest
from app.domain.product import SearchResponse
from app.api.deps import get_chat_intake_service, get_search_service

router = APIRouter()


@router.post("/api/search", response_model=SearchResponse)
async def search(request: ChatRequest):
    """
    Execute a complete product search from user query.
    
    Args:
        request: Chat request with user message
        
    Returns:
        SearchResponse with ranked product results
        
    Raises:
        HTTPException: If search fails
    """
    try:
        # Step 1: Parse intent
        intake_service = get_chat_intake_service()
        intake_response = await intake_service.process_intake(request)
        intent = intake_response.intent
        normalized_query = intent.query_text
        
        # Step 2: Execute search
        search_service = get_search_service()
        return await search_service.search(intent, normalized_query)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

