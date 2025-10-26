"""Miscellaneous API endpoints (health, diagnostics, image proxy)."""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from app.utils.config import PARALLEL_API_KEY
from app.adapters.http_fetch import stream_image

router = APIRouter()


@router.get("/healthz")
async def healthz():
    """
    Health check endpoint.
    
    Returns:
        Status dictionary
    """
    return {"status": "ok"}


@router.get("/api/diag")
async def diagnostics():
    """
    Diagnostics endpoint for checking configuration.
    
    Returns:
        Diagnostics information
    """
    return {
        "has_api_key": bool(PARALLEL_API_KEY),
        "api_key_length": len(PARALLEL_API_KEY) if PARALLEL_API_KEY else 0
    }


@router.get("/api/image-proxy")
async def image_proxy(url: str):
    """
    Proxy images to avoid CORS and hotlinking issues.
    
    Args:
        url: Image URL to proxy
        
    Returns:
        StreamingResponse with image content
        
    Raises:
        HTTPException: If image fetch fails
    """
    try:
        image_bytes, content_type = await stream_image(url)
        
        return StreamingResponse(
            iter([image_bytes]),
            media_type=content_type,
            headers={
                "Cache-Control": "public, max-age=86400",
                "Access-Control-Allow-Origin": "*"
            }
        )
    except Exception as e:
        print(f"Image proxy failed for {url}: {str(e)}")
        raise HTTPException(status_code=404, detail="Image not found")

