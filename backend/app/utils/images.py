"""Image validation and extraction utilities."""
import httpx
from typing import Dict, List, Optional
from app.utils.config import IMAGE_TIMEOUT


async def validate_image(url: str) -> bool:
    """
    Validate image URL with lightweight GET request.
    
    Args:
        url: Image URL to validate
        
    Returns:
        True if the URL points to a valid image
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8"
        }
        async with httpx.AsyncClient(timeout=IMAGE_TIMEOUT) as http_client:
            async with http_client.stream("GET", url, headers=headers, follow_redirects=True) as response:
                if response.status_code == 200:
                    content_type = response.headers.get("content-type", "")
                    if content_type.startswith("image/"):
                        return True
                    if url.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.gif')):
                        return True
        return False
    except Exception:
        if url.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.gif')):
            return True
        return False


async def get_page_media(url: str, extract_client) -> Dict[str, any]:
    """
    Extract images from page using Extract API.
    
    Args:
        url: Page URL to extract media from
        extract_client: Extract API client
        
    Returns:
        Dictionary with images list and primary image URL
    """
    try:
        data = await extract_client.extract(url)
        
        images = []
        primary = None
        
        metadata = data.get("metadata", {})
        if metadata.get("og:image"):
            images.append({"url": metadata["og:image"], "width": None, "height": None, "alt": "og:image"})
            primary = metadata["og:image"]
        if metadata.get("twitter:image") and metadata.get("twitter:image") != primary:
            images.append({"url": metadata["twitter:image"], "width": None, "height": None, "alt": "twitter:image"})
            if not primary:
                primary = metadata["twitter:image"]
        
        content = data.get("content", "")
        if "schema.org/Product" in content or '"@type":"Product"' in content:
            try:
                import re
                import json
                json_ld_match = re.search(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', content, re.DOTALL)
                if json_ld_match:
                    json_ld = json.loads(json_ld_match.group(1))
                    if isinstance(json_ld, dict) and json_ld.get("@type") == "Product":
                        product_images = json_ld.get("image", [])
                        if isinstance(product_images, str):
                            product_images = [product_images]
                        for img_url in product_images[:3]:
                            if img_url not in [i["url"] for i in images]:
                                images.append({"url": img_url, "width": None, "height": None, "alt": "product image"})
                                if not primary:
                                    primary = img_url
            except Exception:
                pass
        
        return {"images": images, "primary": primary}
    except Exception as e:
        print(f"Extract API failed for {url}: {str(e)}")
        return {"images": [], "primary": None}


