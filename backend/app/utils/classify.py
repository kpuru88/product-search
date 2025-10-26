"""Page classification utilities."""
import json
import re
from urllib.parse import urlparse
from typing import Dict, List


async def classify_page(url: str, html: str) -> Dict[str, any]:
    """
    Classify a page as homepage, listing, or product detail page (PDP).
    
    Args:
        url: URL of the page
        html: HTML content of the page
        
    Returns:
        Dictionary with type, reasons, and jsonld_types
    """
    parsed = urlparse(url)
    path = parsed.path.lower()
    
    page_type = "pdp"
    reasons = []
    jsonld_types = []
    
    try:
        jsonld_pattern = r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>'
        jsonld_blocks = re.findall(jsonld_pattern, html, re.DOTALL | re.IGNORECASE)
        
        for block in jsonld_blocks:
            try:
                data = json.loads(block)
                
                def extract_types(obj, types_list):
                    if isinstance(obj, dict):
                        if '@type' in obj:
                            type_val = obj['@type']
                            if isinstance(type_val, list):
                                types_list.extend(type_val)
                            else:
                                types_list.append(type_val)
                        for value in obj.values():
                            if isinstance(value, (dict, list)):
                                extract_types(value, types_list)
                    elif isinstance(obj, list):
                        for item in obj:
                            extract_types(item, types_list)
                
                extract_types(data, jsonld_types)
            except:
                continue
    except:
        pass
    
    if path in ['', '/'] or len(path) <= 2:
        page_type = "homepage"
        reasons.append("URL path is root or very short")
    elif any(t in jsonld_types for t in ['WebSite', 'Organization']) and not any(t in jsonld_types for t in ['Product', 'ItemList']):
        page_type = "homepage"
        reasons.append("JSON-LD contains only WebSite/Organization")
    elif any(pattern in path for pattern in ['/shop/', '/category/', '/search', '/browse', '/c/', '/pl/', '/products/', '/collections/']):
        page_type = "listing"
        reasons.append("URL contains listing/category patterns")
    elif '?q=' in url or '?s=' in url or 'search=' in url.lower():
        page_type = "listing"
        reasons.append("URL contains search query params")
    elif any(t in jsonld_types for t in ['ItemList', 'SearchResultsPage', 'CollectionPage']):
        page_type = "listing"
        reasons.append("JSON-LD contains ItemList/SearchResultsPage")
    elif 'Product' in jsonld_types and any(pattern in path for pattern in ['/product/', '/p/', '/dp/', '/sku/', '/item/']):
        page_type = "pdp"
        reasons.append("JSON-LD Product + PDP URL pattern")
    
    price_count = len(re.findall(r'\$\s*\d+(?:,\d{3})*(?:\.\d{2})?', html[:50000]))
    if price_count > 10 and page_type != "homepage":
        if page_type == "pdp":
            page_type = "listing"
        reasons.append(f"Multiple prices found ({price_count})")
    
    return {
        "type": page_type,
        "reasons": reasons,
        "jsonld_types": jsonld_types
    }


def detect_listing_page(url: str, content: str) -> bool:
    """
    Detect if URL is a category/listing page vs a product detail page.
    
    Args:
        url: URL to check
        content: Page content excerpt
        
    Returns:
        True if the page appears to be a listing page
    """
    url_lower = url.lower()
    
    listing_indicators = ['/search', '/browse', '/category', '/shop', '/s?', '/b/', '/c/', '/results']
    if any(indicator in url_lower for indicator in listing_indicators):
        return True
    
    if '"@type":"ItemList"' in content or '"@type": "ItemList"' in content:
        return True
    
    return False


def get_allowed_product_types(normalized_query: str) -> List[str]:
    """
    Determine allowed product types based on normalized query.
    
    Args:
        normalized_query: Normalized search query
        
    Returns:
        List of allowed product type strings
    """
    query_lower = normalized_query.lower()
    
    if "chair" in query_lower:
        if any(word in query_lower for word in ["accent", "club", "barrel", "vanity", "slipper"]):
            return ["accent chair", "club chair", "barrel chair", "vanity chair", "slipper chair", "armchair"]
        elif "office" in query_lower or "desk" in query_lower:
            return ["office chair", "desk chair", "task chair"]
        elif "gaming" in query_lower:
            return ["gaming chair"]
        else:
            return ["accent chair", "club chair", "barrel chair", "vanity chair", "slipper chair", "armchair", "side chair", "dining chair"]
    
    if any(word in query_lower for word in ["sofa", "couch"]):
        return ["sofa", "couch", "loveseat", "sectional", "sleeper sofa"]
    
    return []

