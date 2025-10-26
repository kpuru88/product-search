"""Parallel AI chat/completion adapter."""
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from app.utils.config import PARALLEL_API_KEY, PARALLEL_BASE_URL
from app.utils.retry import retry_with_backoff


class ParallelChatClient:
    """Wrapper for Parallel AI chat completions."""
    
    def __init__(self):
        """Initialize the Parallel chat client."""
        self.client = AsyncOpenAI(
            api_key=PARALLEL_API_KEY,
            base_url=PARALLEL_BASE_URL
        )
    
    async def create_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "speed",
        response_format: Optional[Dict[str, str]] = None
    ) -> Any:
        """
        Create a chat completion using Parallel AI.
        
        Args:
            messages: List of message dictionaries with role and content
            model: Model to use (default: "speed")
            response_format: Optional response format specification
            
        Returns:
            Completion response object
            
        Raises:
            Exception: If the API call fails after retries
        """
        async def call_api():
            kwargs = {
                "model": model,
                "messages": messages
            }
            if response_format:
                kwargs["response_format"] = response_format
            
            return await self.client.chat.completions.create(**kwargs)
        
        return await retry_with_backoff(call_api)


