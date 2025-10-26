"""Parallel AI search adapter."""
import httpx
from typing import Dict, Any, List
from app.utils.config import PARALLEL_API_KEY, API_TIMEOUT
from app.utils.retry import retry_with_backoff


class ParallelSearchClient:
    """Wrapper for Parallel AI search API."""
    
    def __init__(self):
        """Initialize the Parallel search client."""
        self.api_key = PARALLEL_API_KEY
        self.base_url = "https://api.parallel.ai/v1beta/search"
    
    async def search(
        self,
        objective: str,
        processor: str = "base",
        max_results: int = 10
    ) -> Dict[str, Any]:
        """
        Perform a search using Parallel AI.
        
        Args:
            objective: Search objective describing what to find
            processor: Processor type to use (default: "base")
            max_results: Maximum number of results to return
            
        Returns:
            Dictionary with search results
            
        Raises:
            Exception: If the search fails after retries
        """
        async def call_api():
            async with httpx.AsyncClient(timeout=API_TIMEOUT) as http_client:
                response = await http_client.post(
                    self.base_url,
                    headers={
                        "x-api-key": self.api_key,
                        "Content-Type": "application/json"
                    },
                    json={
                        "objective": objective,
                        "processor": processor,
                        "max_results": max_results
                    }
                )
                response.raise_for_status()
                return response.json()
        
        return await retry_with_backoff(call_api)
    
    def get_results(self, search_response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract results list from search response.
        
        Args:
            search_response: Response from search API
            
        Returns:
            List of search result dictionaries
        """
        return search_response.get("results", [])


