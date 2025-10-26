"""Retry utilities with exponential backoff."""
import asyncio
from typing import Callable, TypeVar, Awaitable

T = TypeVar('T')


async def retry_with_backoff(
    func: Callable[[], Awaitable[T]], 
    max_retries: int = 2
) -> T:
    """
    Retry an async function with exponential backoff.
    
    Args:
        func: Async function to retry
        max_retries: Maximum number of retry attempts
        
    Returns:
        Result from the function
        
    Raises:
        Exception: Re-raises the last exception if all retries fail
    """
    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            if "429" in str(e) or "5" in str(e)[:1]:
                wait_time = (2 ** attempt) * 1
                await asyncio.sleep(wait_time)
            else:
                raise

