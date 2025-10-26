"""Parallel AI extract adapter."""
import httpx
from typing import Dict, Any
from app.utils.config import PARALLEL_API_KEY, EXTRACT_TIMEOUT


class ParallelExtractClient:
    """Wrapper for Parallel AI extract API."""
    
    def __init__(self):
        """Initialize the Parallel extract client."""
        self.api_key = PARALLEL_API_KEY
        self.base_url = "https://api.parallel.ai/v1beta/extract"
    
    async def extract(self, url: str) -> Dict[str, Any]:
        """
        Extract content and metadata from a URL.
        
        Args:
            url: URL to extract content from
            
        Returns:
            Dictionary with extracted content and metadata
            
        Raises:
            Exception: If extraction fails
        """
        async with httpx.AsyncClient(timeout=EXTRACT_TIMEOUT) as http_client:
            response = await http_client.post(
                self.base_url,
                headers={
                    "x-api-key": self.api_key,
                    "Content-Type": "application/json"
                },
                json={"url": url}
            )
            response.raise_for_status()
            return response.json()
    
    async def extract_with_auth_header(self, url: str) -> Dict[str, Any]:
        """
        Extract content using Bearer token authentication (alternative auth method).
        
        Args:
            url: URL to extract content from
            
        Returns:
            Dictionary with extracted content and metadata
            
        Raises:
            Exception: If extraction fails
        """
        async with httpx.AsyncClient(timeout=API_TIMEOUT) as http_client:
            response = await http_client.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={"url": url}
            )
            response.raise_for_status()
            return response.json()


# Import for timeout constant
from app.utils.config import API_TIMEOUT


