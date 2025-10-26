"""Chat intake service for parsing user queries into structured intents."""
import json
from typing import Optional
from app.domain.intent import SearchIntent
from app.domain.chat import ChatRequest, ChatIntakeResponse
from app.adapters.parallel_chat import ParallelChatClient
from app.utils.normalization import normalize_name


class ChatIntakeService:
    """Service for processing chat intake and extracting search intent."""
    
    def __init__(self, chat_client: ParallelChatClient):
        """
        Initialize the chat intake service.
        
        Args:
            chat_client: Parallel chat client for LLM calls
        """
        self.chat_client = chat_client
    
    def _build_intent_extraction_prompt(self, message: str) -> list:
        """
        Build prompt for extracting search intent from user message.
        
        Args:
            message: User's raw message
            
        Returns:
            List of message dictionaries for the LLM
        """
        return [
            {
                "role": "system",
                "content": "You are a retail product triage assistant. Extract a structured search intent from the user's text. Output ONLY a JSON object with these fields: query_text (string), category (string or null), brand (string or null), model (string or null), core_specs (array of strings), price_expectation (string or null), region (string, default 'US'), strictness (must be exactly 'exact', 'close', or 'fuzzy', default 'close')."
            },
            {
                "role": "user",
                "content": f"Extract search intent from: {message}\n\nReturn ONLY JSON with the exact field names and types specified. For strictness, use ONLY 'exact', 'close', or 'fuzzy'. No other text."
            }
        ]
    
    async def process_intake(self, request: ChatRequest) -> ChatIntakeResponse:
        """
        Process a chat intake request and extract structured search intent.
        
        Args:
            request: Chat request with user message
            
        Returns:
            ChatIntakeResponse with parsed intent
            
        Raises:
            Exception: If intent extraction fails
        """
        messages = self._build_intent_extraction_prompt(request.message)
        
        response = await self.chat_client.create_completion(
            messages=messages,
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content.strip()
        
        try:
            intent_data = json.loads(content)
        except json.JSONDecodeError:
            intent_data = {
                "query_text": request.message,
                "category": None,
                "brand": None,
                "model": None,
                "core_specs": [],
                "price_expectation": None,
                "region": "US",
                "strictness": "close"
            }
        
        # Set defaults
        if "region" not in intent_data:
            intent_data["region"] = "US"
        if "strictness" not in intent_data:
            intent_data["strictness"] = "close"
        if "core_specs" not in intent_data:
            intent_data["core_specs"] = []
        
        intent = SearchIntent(**intent_data)
        
        # Normalize the query text
        normalized = await normalize_name(intent.query_text, self.chat_client)
        intent.query_text = normalized.get("normalized_query", intent.query_text)
        
        return ChatIntakeResponse(intent=intent)

