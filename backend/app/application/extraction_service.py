"""Product extraction service for extracting structured data from pages."""
import json
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse
from app.adapters.parallel_chat import ParallelChatClient
from app.adapters.parallel_extract import ParallelExtractClient
from app.utils.domains import get_domain_tier, get_tier_name
from app.utils.classify import detect_listing_page
from app.utils.normalization import normalize_name
from app.utils.images import validate_image, get_page_media
from app.utils.price import extract_price_range
from app.domain.product import ProductItem, Image


class ExtractionService:
    """Service for extracting product details from web pages."""
    
    def __init__(
        self, 
        chat_client: ParallelChatClient,
        extract_client: ParallelExtractClient
    ):
        """
        Initialize the extraction service.
        
        Args:
            chat_client: Parallel chat client for LLM calls
            extract_client: Parallel extract client for content extraction
        """
        self.chat_client = chat_client
        self.extract_client = extract_client
    
    def _build_extraction_prompt(
        self, 
        url: str, 
        excerpt_text: str, 
        normalized_query: str, 
        tier_name: str
    ) -> list:
        """
        Build prompt for extracting product details from content.
        
        Args:
            url: Product page URL
            excerpt_text: Content excerpt from the page
            normalized_query: Normalized search query
            tier_name: Domain tier name (manufacturer, major retailer, etc.)
            
        Returns:
            List of message dictionaries for the LLM
        """
        allowed_types_str = "any product type"
        
        return [
            {
                "role": "system",
                "content": "You extract structured product data from ecommerce PDPs. Prefer official title, price, currency, availability, model, and review snippets. Also extract image candidates (primary image + gallery). Return strict JSON per schema."
            },
            {
                "role": "user",
                "content": f"""User normalized query: {normalized_query}
Domain priority: {tier_name}
URL: {url}
CONTENT: {excerpt_text[:3000]}

Return JSON:
{{
  "title": string,
  "normalized_title": string,
  "price": number | null,
  "currency": string | null,
  "availability": string | null,
  "model": string | null,
  "match_score": number,
  "review_snippets": string[],
  "images": [{{"url": string, "width": number|null, "height": number|null, "alt": string|null}}],
  "primary_image_url": string | null,
  "product_type": string,
  "category_match": boolean
}}

Rules:
- normalized_title: max 3 tokens (2-4 words), e.g., "black accent chair"
- match_score: 0-1 vs normalized_query
- product_type: classify as one of: accent chair, club chair, barrel chair, office chair, gaming chair, sofa, loveseat, sectional, couch, desk, table, or other
- category_match: true if product_type matches query intent. Query expects: {allowed_types_str}
- Prefer gallery/hero images; fall back to og:image/twitter:image if available

Return ONLY JSON, no other text."""
            }
        ]
    
    async def _extract_from_llm(self, messages: list) -> Optional[Dict[str, Any]]:
        """
        Call LLM to extract product data from content.
        
        Args:
            messages: Prompt messages for the LLM
            
        Returns:
            Extracted product data dictionary or None if extraction fails
        """
        try:
            response = await self.chat_client.create_completion(
                messages=messages,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content.strip()
            
            try:
                product_data = json.loads(content)
                return product_data
            except json.JSONDecodeError:
                return None
        except Exception as e:
            print(f"LLM extraction failed: {str(e)}")
            return None
    
    async def extract_product_details(
        self, 
        url: str, 
        excerpts: List[str], 
        normalized_query: str
    ) -> Optional[Dict[str, Any]]:
        """
        Extract product details from a URL and its content excerpts.
        
        Args:
            url: Product page URL
            excerpts: Content excerpts from search results
            normalized_query: Normalized search query
            
        Returns:
            Dictionary with extracted product data or None if extraction fails
        """
        try:
            excerpt_text = " ".join(excerpts[:3]) if excerpts else ""
            domain_tier = get_domain_tier(url)
            tier_name = get_tier_name(domain_tier)
            
            is_listing = detect_listing_page(url, excerpt_text)
            
            # Build prompt and extract data from LLM
            messages = self._build_extraction_prompt(url, excerpt_text, normalized_query, tier_name)
            product_data = await self._extract_from_llm(messages)
            
            if not product_data:
                return None
            
            product_data["url"] = url
            
            # Set defaults for missing fields
            if "currency" not in product_data:
                product_data["currency"] = "USD"
            if "match_score" not in product_data:
                product_data["match_score"] = 0.5
            if "review_snippets" not in product_data:
                product_data["review_snippets"] = []
            if "images" not in product_data:
                product_data["images"] = []
            if "primary_image_url" not in product_data:
                product_data["primary_image_url"] = None
            if "product_type" not in product_data:
                product_data["product_type"] = "other"
            if "category_match" not in product_data:
                product_data["category_match"] = True
            
            # Normalize title if not provided
            if "normalized_title" not in product_data or not product_data["normalized_title"]:
                if "title" in product_data:
                    normalized = await normalize_name(product_data["title"], self.chat_client)
                    product_data["normalized_title"] = normalized.get("normalized_query", product_data["title"])
            
            # Fetch images if missing
            if not product_data.get("primary_image_url") or not product_data.get("images"):
                media = await get_page_media(url, self.extract_client)
                if media["primary"] and not product_data.get("primary_image_url"):
                    product_data["primary_image_url"] = media["primary"]
                if media["images"] and not product_data.get("images"):
                    product_data["images"] = media["images"]
            
            # Validate primary image
            if product_data.get("primary_image_url"):
                is_valid = await validate_image(product_data["primary_image_url"])
                if not is_valid:
                    for img in product_data.get("images", []):
                        if await validate_image(img.get("url", "")):
                            product_data["primary_image_url"] = img["url"]
                            break
            
            product_data["is_listing_page"] = is_listing
            
            # Extract price range for listing pages
            if is_listing and not product_data.get("price"):
                try:
                    extract_data = await self.extract_client.extract_with_auth_header(url)
                    full_content = extract_data.get("content", "")
                    print(f"Fetched full content for listing page {url}: {len(full_content)} chars")
                    price_range = await extract_price_range(full_content)
                except Exception as e:
                    print(f"Extract API call failed for {url}: {str(e)}")
                    price_range = await extract_price_range(excerpt_text)
                
                product_data["price_min"] = price_range.get("price_min")
                product_data["price_max"] = price_range.get("price_max")
            
            return product_data
        
        except Exception as e:
            print(f"Product extraction failed for {url}: {str(e)}")
            return None

