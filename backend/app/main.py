from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
import os
from dotenv import load_dotenv
import httpx
import json
import asyncio
from openai import AsyncOpenAI

load_dotenv()

app = FastAPI()

# Disable CORS. Do not remove this for full-stack development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

PARALLEL_API_KEY = os.getenv("PARALLEL_API_KEY")
if not PARALLEL_API_KEY:
    raise ValueError("PARALLEL_API_KEY environment variable is required")

client = AsyncOpenAI(
    api_key=PARALLEL_API_KEY,
    base_url="https://api.parallel.ai"
)

class SearchIntent(BaseModel):
    query_text: str
    category: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    core_specs: List[str] = Field(default_factory=list)
    price_expectation: Optional[str] = None
    region: str = "US"
    strictness: Literal["exact", "close", "fuzzy"] = "close"

class Image(BaseModel):
    url: str
    width: Optional[int] = None
    height: Optional[int] = None
    alt: Optional[str] = None

class ProductItem(BaseModel):
    title: str
    normalized_title: Optional[str] = None
    price: Optional[float] = None
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    currency: Optional[str] = "USD"
    url: str
    source: str
    match_score: float
    review_sentiment: Literal["positive", "neutral", "negative", "unknown"] = "unknown"
    sentiment_score: Optional[float] = None
    fake_review_probability: Optional[float] = None
    availability: Optional[str] = None
    primary_image_url: Optional[str] = None
    images: List[Image] = Field(default_factory=list)
    sentiment_reason: Optional[str] = None
    sentiment_highlights: List[str] = Field(default_factory=list)
    product_type: Optional[str] = None
    category_match: Optional[bool] = None
    is_listing_page: Optional[bool] = False

class SearchResponse(BaseModel):
    query: str
    items: List[ProductItem]

class ChatRequest(BaseModel):
    message: str

class ChatIntakeResponse(BaseModel):
    intent: SearchIntent
    clarification: Optional[str] = None

async def retry_with_backoff(func, max_retries=2):
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

MANUFACTURER_DOMAINS = ["apple.com", "samsung.com", "sony.com", "lg.com", "dell.com", "hp.com", "microsoft.com", "google.com", "lenovo.com", "asus.com"]
MAJOR_RETAILERS = ["amazon.com", "bestbuy.com", "walmart.com", "target.com", "homedepot.com", "wayfair.com", "ikea.com", "crateandbarrel.com", "lowes.com", "overstock.com", "ebay.com", "etsy.com", "costco.com", "macys.com"]
MARKETPLACES = ["ebay.com", "etsy.com", "mercari.com", "poshmark.com", "offerup.com"]

def get_domain_tier(url: str) -> int:
    from urllib.parse import urlparse
    domain = urlparse(url).netloc.replace("www.", "").lower()
    
    if any(mfr in domain for mfr in MANUFACTURER_DOMAINS):
        return 3
    if any(retailer in domain for retailer in MAJOR_RETAILERS):
        return 2
    if any(market in domain for market in MARKETPLACES):
        return 1
    return 0

def is_ecommerce_domain(url: str) -> bool:
    tier = get_domain_tier(url)
    return tier > 0

async def normalize_name(text: str) -> dict:
    try:
        async def call_normalizer():
            response = await client.chat.completions.create(
                model="speed",
                messages=[
                    {
                        "role": "system",
                        "content": "You normalize retail product names. Output compact, literal phrases that capture the core item. Keep color and one or two critical qualifiers (size, model family). Drop pack counts, marketing adjectives, and usage contexts. Max ~3 tokens (2-4 words). Return JSON only per schema."
                    },
                    {
                        "role": "user",
                        "content": f"""Normalize this product name: {text}

Return ONLY JSON with these fields:
- normalized_query: string (e.g., "black accent chair")
- keywords: array of strings (e.g., ["accent chair", "black", "vanity"])
- keep_model: boolean (true if a model id must be preserved)

Examples:
"Yaheetech Black Accent Chairs Set of 2, Cozy Velvet Barrel Chair..." → {{"normalized_query": "black accent chair", "keywords": ["accent chair", "black", "vanity"], "keep_model": false}}
"Apple iPhone 16 Pro Max 256GB (Model XYZ123)" → {{"normalized_query": "iPhone 16 Pro Max", "keywords": ["iPhone", "16 Pro Max"], "keep_model": true}}
"Samsung 75-inch QLED 4K Smart TV" → {{"normalized_query": "75-inch QLED TV", "keywords": ["QLED TV", "75-inch", "Samsung"], "keep_model": false}}

Return ONLY JSON, no other text."""
                    }
                ],
                response_format={"type": "json_object"}
            )
            return response
        
        response = await retry_with_backoff(call_normalizer)
        content = response.choices[0].message.content.strip()
        
        try:
            normalized_data = json.loads(content)
            return normalized_data
        except json.JSONDecodeError:
            return {
                "normalized_query": text,
                "keywords": [text],
                "keep_model": False
            }
    
    except Exception as e:
        print(f"Normalization failed: {str(e)}")
        return {
            "normalized_query": text,
            "keywords": [text],
            "keep_model": False
        }

async def validate_image(url: str) -> bool:
    """Validate image URL with lightweight GET request"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8"
        }
        async with httpx.AsyncClient(timeout=4.0) as http_client:
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

async def get_page_media(url: str) -> dict:
    """Extract images from page using Extract API"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as http_client:
            response = await http_client.post(
                "https://api.parallel.ai/v1beta/extract",
                headers={
                    "x-api-key": PARALLEL_API_KEY,
                    "Content-Type": "application/json"
                },
                json={"url": url}
            )
            response.raise_for_status()
            data = response.json()
            
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

def get_allowed_product_types(normalized_query: str) -> List[str]:
    """Determine allowed product types based on normalized query"""
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

async def fetch_html(url: str) -> Optional[str]:
    """Fetch HTML content with httpx GET fallback"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            response = await client.get(url, headers=headers)
            if response.status_code == 200:
                return response.text
            else:
                print(f"Failed to fetch HTML for {url}: {response.status_code}")
                return None
    except Exception as e:
        print(f"HTML fetch failed for {url}: {str(e)}")
        return None

async def classify_page(url: str, html: str) -> dict:
    """Classify page as homepage, listing, or PDP"""
    from urllib.parse import urlparse
    import re
    
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

async def expand_listing(url: str, html: str, max_products: int = 5) -> List[dict]:
    """Extract individual product URLs and prices from listing page"""
    import re
    from urllib.parse import urljoin, urlparse
    
    products = []
    
    try:
        jsonld_pattern = r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>'
        jsonld_blocks = re.findall(jsonld_pattern, html, re.DOTALL | re.IGNORECASE)
        
        for block in jsonld_blocks:
            try:
                data = json.loads(block)
                
                def extract_products_from_jsonld(obj):
                    if isinstance(obj, dict):
                        if obj.get('@type') == 'ItemList' and 'itemListElement' in obj:
                            for item in obj['itemListElement']:
                                if isinstance(item, dict):
                                    product_obj = item.get('item', item)
                                    if isinstance(product_obj, dict):
                                        product_url = product_obj.get('url')
                                        product_name = product_obj.get('name')
                                        
                                        price = None
                                        currency = None
                                        
                                        if 'offers' in product_obj:
                                            offers = product_obj['offers']
                                            if isinstance(offers, dict):
                                                price = offers.get('price') or offers.get('lowPrice')
                                                currency = offers.get('priceCurrency', 'USD')
                                            elif isinstance(offers, list) and len(offers) > 0:
                                                price = offers[0].get('price')
                                                currency = offers[0].get('priceCurrency', 'USD')
                                        
                                        if product_url:
                                            products.append({
                                                'url': urljoin(url, product_url),
                                                'title': product_name,
                                                'price': float(price) if price else None,
                                                'currency': currency
                                            })
                        
                        elif obj.get('@type') == 'Product':
                            product_url = obj.get('url')
                            product_name = obj.get('name')
                            
                            price = None
                            currency = None
                            
                            if 'offers' in obj:
                                offers = obj['offers']
                                if isinstance(offers, dict):
                                    price = offers.get('price') or offers.get('lowPrice')
                                    currency = offers.get('priceCurrency', 'USD')
                                elif isinstance(offers, list) and len(offers) > 0:
                                    price = offers[0].get('price')
                                    currency = offers[0].get('priceCurrency', 'USD')
                            
                            if product_url:
                                products.append({
                                    'url': urljoin(url, product_url),
                                    'title': product_name,
                                    'price': float(price) if price else None,
                                    'currency': currency
                                })
                        
                        for value in obj.values():
                            if isinstance(value, (dict, list)):
                                extract_products_from_jsonld(value)
                    
                    elif isinstance(obj, list):
                        for item in obj:
                            extract_products_from_jsonld(item)
                
                extract_products_from_jsonld(data)
            except:
                continue
    except:
        pass
    
    if len(products) < max_products:
        link_patterns = [
            r'<a[^>]*href=["\']([^"\']*(?:/product/|/p/|/dp/|/sku/|/item/)[^"\']*)["\']',
            r'<a[^>]*data-asin=["\']([^"\']+)["\']',
            r'<a[^>]*data-sku=["\']([^"\']+)["\']',
        ]
        
        for pattern in link_patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            for match in matches[:max_products * 2]:
                if match.startswith('http'):
                    product_url = match
                else:
                    product_url = urljoin(url, match)
                
                if product_url not in [p['url'] for p in products]:
                    products.append({
                        'url': product_url,
                        'title': None,
                        'price': None,
                        'currency': 'USD'
                    })
                
                if len(products) >= max_products:
                    break
            
            if len(products) >= max_products:
                break
    
    seen_urls = set()
    unique_products = []
    for p in products:
        if p['url'] not in seen_urls:
            seen_urls.add(p['url'])
            unique_products.append(p)
    
    print(f"Expanded listing {url}: found {len(unique_products)} products")
    return unique_products[:max_products]

def detect_listing_page(url: str, content: str) -> bool:
    """Detect if URL is a category/listing page vs a product detail page"""
    url_lower = url.lower()
    
    listing_indicators = ['/search', '/browse', '/category', '/shop', '/s?', '/b/', '/c/', '/results']
    if any(indicator in url_lower for indicator in listing_indicators):
        return True
    
    if '"@type":"ItemList"' in content or '"@type": "ItemList"' in content:
        return True
    
    return False

async def extract_price_range(content: str) -> dict:
    """Extract price range from listing page content using JSON-LD and regex"""
    try:
        import re
        import json
        
        prices = []
        
        try:
            jsonld_pattern = r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>'
            jsonld_blocks = re.findall(jsonld_pattern, content, re.DOTALL | re.IGNORECASE)
            
            for block in jsonld_blocks:
                try:
                    data = json.loads(block)
                    
                    def extract_prices_from_jsonld(obj):
                        if isinstance(obj, dict):
                            if obj.get('@type') == 'AggregateOffer':
                                if 'lowPrice' in obj:
                                    try:
                                        prices.append(float(str(obj['lowPrice']).replace(',', '')))
                                    except (ValueError, TypeError):
                                        pass
                                if 'highPrice' in obj:
                                    try:
                                        prices.append(float(str(obj['highPrice']).replace(',', '')))
                                    except (ValueError, TypeError):
                                        pass
                            
                            if obj.get('@type') in ['Offer', 'Product']:
                                if 'price' in obj:
                                    try:
                                        prices.append(float(str(obj['price']).replace(',', '')))
                                    except (ValueError, TypeError):
                                        pass
                                if 'offers' in obj:
                                    extract_prices_from_jsonld(obj['offers'])
                            
                            if obj.get('@type') == 'ItemList' and 'itemListElement' in obj:
                                for item in obj['itemListElement']:
                                    if isinstance(item, dict):
                                        if 'item' in item:
                                            extract_prices_from_jsonld(item['item'])
                                        else:
                                            extract_prices_from_jsonld(item)
                            
                            for value in obj.values():
                                if isinstance(value, (dict, list)):
                                    extract_prices_from_jsonld(value)
                        
                        elif isinstance(obj, list):
                            for item in obj:
                                extract_prices_from_jsonld(item)
                    
                    extract_prices_from_jsonld(data)
                except json.JSONDecodeError:
                    continue
        except Exception as e:
            print(f"JSON-LD parsing failed: {str(e)}")
        
        price_patterns = [
            r'\$\s*(\d+(?:,\d{3})*(?:\.\d{2})?)',  # Standard $199 or $1,999.99
            r'(?:From|from|Starting at|starting at)\s+\$\s*(\d+(?:,\d{3})*(?:\.\d{2})?)',  # From $199
            r'(?:Now|now|Sale|sale|SALE)\s+\$\s*(\d+(?:,\d{3})*(?:\.\d{2})?)',  # Now $199, Sale $199
            r'\$\s*(\d+(?:,\d{3})*(?:\.\d{2})?)\s*[-–—]\s*\$\s*(\d+(?:,\d{3})*(?:\.\d{2})?)',  # $199–$399 (range)
        ]
        
        for pattern in price_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    for price_str in match:
                        try:
                            price = float(price_str.replace(',', ''))
                            if 5 <= price <= 100000:
                                prices.append(price)
                        except ValueError:
                            continue
                else:
                    try:
                        price = float(match.replace(',', ''))
                        if 5 <= price <= 100000:
                            prices.append(price)
                    except ValueError:
                        continue
        
        if not prices:
            print(f"No prices found in content (length: {len(content)} chars)")
            return {"price_min": None, "price_max": None}
        
        prices = sorted(set(prices))
        print(f"Found {len(prices)} unique prices: {prices[:10]}...")  # Log first 10 for debugging
        
        return {
            "price_min": min(prices),
            "price_max": max(prices)
        }
    except Exception as e:
        print(f"Price range extraction failed: {str(e)}")
        return {"price_min": None, "price_max": None}

@app.post("/api/chat/intake", response_model=ChatIntakeResponse)
async def chat_intake(request: ChatRequest):
    try:
        async def call_chat():
            response = await client.chat.completions.create(
                model="speed",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a retail product triage assistant. Extract a structured search intent from the user's text. Output ONLY a JSON object with these fields: query_text (string), category (string or null), brand (string or null), model (string or null), core_specs (array of strings), price_expectation (string or null), region (string, default 'US'), strictness (must be exactly 'exact', 'close', or 'fuzzy', default 'close')."
                    },
                    {
                        "role": "user",
                        "content": f"Extract search intent from: {request.message}\n\nReturn ONLY JSON with the exact field names and types specified. For strictness, use ONLY 'exact', 'close', or 'fuzzy'. No other text."
                    }
                ],
                response_format={"type": "json_object"}
            )
            return response
        
        response = await retry_with_backoff(call_chat)
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
        
        if "region" not in intent_data:
            intent_data["region"] = "US"
        if "strictness" not in intent_data:
            intent_data["strictness"] = "close"
        if "core_specs" not in intent_data:
            intent_data["core_specs"] = []
            
        intent = SearchIntent(**intent_data)
        
        normalized = await normalize_name(intent.query_text)
        intent.query_text = normalized.get("normalized_query", intent.query_text)
        
        return ChatIntakeResponse(intent=intent)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat intake failed: {str(e)}")

async def search_products(intent: SearchIntent, normalized_query: str) -> List[dict]:
    try:
        manufacturer_domains = ", ".join(MANUFACTURER_DOMAINS[:5])
        retailer_domains = ", ".join(MAJOR_RETAILERS[:10])
        
        objective = f"""Find US ecommerce product detail pages (PDPs) for: "{normalized_query}". 
Strictly prioritize PDPs from: {manufacturer_domains}, {retailer_domains}. 
Return product detail pages that show current price for a single product. 
Avoid category/search/listing pages unless not enough PDPs are available.
Exclude forums/news/review-only pages. 
Include synonyms where helpful (e.g., "sofa" for "couch"). Provide at least 8 PDPs if available."""
        
        async def call_search():
            async with httpx.AsyncClient(timeout=30.0) as http_client:
                response = await http_client.post(
                    "https://api.parallel.ai/v1beta/search",
                    headers={
                        "x-api-key": PARALLEL_API_KEY,
                        "Content-Type": "application/json"
                    },
                    json={
                        "objective": objective,
                        "processor": "base",
                        "max_results": 10
                    }
                )
                response.raise_for_status()
                return response.json()
        
        search_result = await retry_with_backoff(call_search)
        results = search_result.get("results", [])
        
        ecommerce_results = [r for r in results if is_ecommerce_domain(r.get("url", ""))]
        
        if len(ecommerce_results) >= 5:
            return ecommerce_results
        else:
            return results
    
    except Exception as e:
        print(f"Search failed: {str(e)}")
        return []

async def extract_product_details(url: str, excerpts: List[str], normalized_query: str) -> Optional[dict]:
    try:
        excerpt_text = " ".join(excerpts[:3]) if excerpts else ""
        domain_tier = get_domain_tier(url)
        tier_name = "manufacturer" if domain_tier == 3 else "major retailer" if domain_tier == 2 else "marketplace" if domain_tier == 1 else "other"
        
        allowed_types = get_allowed_product_types(normalized_query)
        allowed_types_str = ", ".join(allowed_types) if allowed_types else "any product type"
        
        is_listing = detect_listing_page(url, excerpt_text)
        
        async def call_extract():
            response = await client.chat.completions.create(
                model="speed",
                messages=[
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
                ],
                response_format={"type": "json_object"}
            )
            return response
        
        response = await retry_with_backoff(call_extract)
        content = response.choices[0].message.content.strip()
        
        try:
            product_data = json.loads(content)
        except json.JSONDecodeError:
            return None
            
        product_data["url"] = url
        
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
        
        if "normalized_title" not in product_data or not product_data["normalized_title"]:
            if "title" in product_data:
                normalized = await normalize_name(product_data["title"])
                product_data["normalized_title"] = normalized.get("normalized_query", product_data["title"])
        
        if not product_data.get("primary_image_url") or not product_data.get("images"):
            media = await get_page_media(url)
            if media["primary"] and not product_data.get("primary_image_url"):
                product_data["primary_image_url"] = media["primary"]
            if media["images"] and not product_data.get("images"):
                product_data["images"] = media["images"]
        
        if product_data.get("primary_image_url"):
            is_valid = await validate_image(product_data["primary_image_url"])
            if not is_valid:
                for img in product_data.get("images", []):
                    if await validate_image(img.get("url", "")):
                        product_data["primary_image_url"] = img["url"]
                        break
        
        product_data["is_listing_page"] = is_listing
        
        if is_listing and not product_data.get("price"):
            try:
                async with httpx.AsyncClient(timeout=30.0) as extract_client:
                    extract_response = await extract_client.post(
                        "https://api.parallel.ai/v1beta/extract",
                        headers={
                            "Authorization": f"Bearer {PARALLEL_API_KEY}",
                            "Content-Type": "application/json"
                        },
                        json={"url": url}
                    )
                    if extract_response.status_code == 200:
                        extract_data = extract_response.json()
                        full_content = extract_data.get("content", "")
                        print(f"Fetched full content for listing page {url}: {len(full_content)} chars")
                        price_range = await extract_price_range(full_content)
                    else:
                        print(f"Extract API failed for {url}: {extract_response.status_code}")
                        price_range = await extract_price_range(excerpt_text)
            except Exception as e:
                print(f"Extract API call failed for {url}: {str(e)}")
                price_range = await extract_price_range(excerpt_text)
            
            product_data["price_min"] = price_range.get("price_min")
            product_data["price_max"] = price_range.get("price_max")
        
        return product_data
    
    except Exception as e:
        print(f"Product extraction failed for {url}: {str(e)}")
        return None

async def analyze_reviews(review_snippets: List[str], normalized_title: str = "") -> dict:
    if not review_snippets or len(review_snippets) == 0:
        return {
            "review_sentiment": "unknown",
            "sentiment_score": None,
            "fake_review_probability": None,
            "sentiment_reason": None,
            "sentiment_highlights": []
        }
    
    try:
        async def call_sentiment():
            product_context = f"Product: {normalized_title}\n" if normalized_title else ""
            response = await client.chat.completions.create(
                model="speed",
                messages=[
                    {
                        "role": "system",
                        "content": "You evaluate product reviews and exclude likely fake content before summarizing sentiment. Provide detailed reasoning and evidence."
                    },
                    {
                        "role": "user",
                        "content": f"""{product_context}SNIPPETS: {json.dumps(review_snippets[:10])}

Analyze these review snippets. First, label each snippet as positive/neutral/negative and identify fake ones (repetitive, templated, generic, bursty patterns).

Filter out snippets with fake_review_probability >0.7. Then compute sentiment from the remaining snippets.

Return ONLY JSON with these fields:
- review_sentiment: "positive" or "neutral" or "negative"
- sentiment_score: number 0-1 (based on proportion of positive vs negative in kept snippets, NOT a default 0.85)
- fake_review_probability: number 0-1 (aggregate of kept snippets, e.g., 95th percentile)
- reason: string (1-3 sentences explaining WHY this sentiment, citing specific themes)
- highlights: array of 3-5 strings (concise points extracted from kept snippets, e.g., "Comfortable seating", "Easy assembly", "Great value")

Example:
{{"review_sentiment": "positive", "sentiment_score": 0.78, "fake_review_probability": 0.2, "reason": "Most reviews praise the chair's comfort and sturdy build quality, though some mention minor assembly issues.", "highlights": ["Very comfortable padding", "Sturdy metal frame", "Easy to assemble", "Good value for price", "Stylish design"]}}

Return ONLY JSON, no other text."""
                    }
                ],
                response_format={"type": "json_object"}
            )
            return response
        
        response = await retry_with_backoff(call_sentiment)
        content = response.choices[0].message.content.strip()
        
        try:
            sentiment_data = json.loads(content)
            if "reason" not in sentiment_data:
                sentiment_data["reason"] = None
            if "highlights" not in sentiment_data:
                sentiment_data["highlights"] = []
            return sentiment_data
        except json.JSONDecodeError:
            return {
                "review_sentiment": "unknown",
                "sentiment_score": None,
                "fake_review_probability": None,
                "sentiment_reason": None,
                "sentiment_highlights": []
            }
    
    except Exception as e:
        print(f"Sentiment analysis failed: {str(e)}")
        return {
            "review_sentiment": "unknown",
            "sentiment_score": None,
            "fake_review_probability": None,
            "sentiment_reason": None,
            "sentiment_highlights": []
        }

async def process_product(result: dict, normalized_query: str) -> Optional[ProductItem]:
    try:
        url = result.get("url", "")
        excerpts = result.get("excerpts", [])
        
        if not url:
            return None
        
        product_data = await extract_product_details(url, excerpts, normalized_query)
        
        if not product_data:
            return None
        
        review_snippets = product_data.get("review_snippets", [])
        normalized_title = product_data.get("normalized_title", "")
        sentiment_data = await analyze_reviews(review_snippets, normalized_title)
        
        from urllib.parse import urlparse
        source = urlparse(url).netloc.replace("www.", "")
        
        images = []
        for img in product_data.get("images", []):
            if isinstance(img, dict):
                images.append(Image(
                    url=img.get("url", ""),
                    width=img.get("width"),
                    height=img.get("height"),
                    alt=img.get("alt")
                ))
        
        product = ProductItem(
            title=product_data["title"],
            normalized_title=normalized_title,
            price=product_data.get("price"),
            price_min=product_data.get("price_min"),
            price_max=product_data.get("price_max"),
            currency=product_data.get("currency", "USD"),
            url=url,
            source=source,
            match_score=product_data["match_score"],
            availability=product_data.get("availability"),
            review_sentiment=sentiment_data["review_sentiment"],
            sentiment_score=sentiment_data.get("sentiment_score"),
            fake_review_probability=sentiment_data.get("fake_review_probability"),
            primary_image_url=product_data.get("primary_image_url"),
            images=images,
            sentiment_reason=sentiment_data.get("reason"),
            sentiment_highlights=sentiment_data.get("highlights", []),
            product_type=product_data.get("product_type"),
            category_match=product_data.get("category_match", True),
            is_listing_page=product_data.get("is_listing_page", False)
        )
        
        return product
    except Exception as e:
        print(f"Failed to process product {result.get('url', 'unknown')}: {str(e)}")
        return None

@app.post("/api/search", response_model=SearchResponse)
async def search(request: ChatRequest):
    try:
        intake_response = await chat_intake(request)
        intent = intake_response.intent
        normalized_query = intent.query_text
        
        search_results = await search_products(intent, normalized_query)
        
        if not search_results:
            return SearchResponse(query=normalized_query, items=[])
        
        url_queue = []
        
        for result in search_results[:8]:
            url = result.get("url", "")
            if not url:
                continue
            
            html = await fetch_html(url)
            if not html:
                url_queue.append({"url": url, "page_type": "pdp", "excerpts": result.get("excerpts", [])})
                continue
            
            classification = await classify_page(url, html)
            page_type = classification["type"]
            
            print(f"Classified {url} as {page_type}: {', '.join(classification['reasons'])}")
            
            if page_type == "homepage":
                url_queue.append({"url": url, "page_type": "homepage", "excerpts": result.get("excerpts", [])})
            elif page_type == "listing":
                expanded_products = await expand_listing(url, html, max_products=5)
                for exp_product in expanded_products:
                    url_queue.append({
                        "url": exp_product["url"],
                        "page_type": "pdp",
                        "excerpts": [],
                        "from_listing": url
                    })
                if len(expanded_products) == 0:
                    url_queue.append({"url": url, "page_type": "listing", "excerpts": result.get("excerpts", [])})
            else:
                url_queue.append({"url": url, "page_type": "pdp", "excerpts": result.get("excerpts", [])})
        
        tasks = [process_product(item, normalized_query) for item in url_queue[:10]]
        products_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        products = [p for p in products_results if isinstance(p, ProductItem)]
        
        filtered_products = [p for p in products if p.match_score >= 0.35]
        
        seen_products = set()
        deduped_products = []
        for p in filtered_products:
            key = f"{p.normalized_title}|{p.source}"
            if key not in seen_products:
                seen_products.add(key)
                deduped_products.append(p)
        
        deduped_products.sort(
            key=lambda p: (
                -p.match_score,
                -(1 if p.category_match else 0),
                -(0 if p.is_listing_page else 1),
                -(1 if getattr(p, 'page_type', 'pdp') == 'pdp' else 0),
                -(1 if getattr(p, 'page_type', 'pdp') == 'listing' else 0),
                -get_domain_tier(p.url),
                -(1 if p.price is not None else 0)
            )
        )
        
        return SearchResponse(query=normalized_query, items=deduped_products[:6])
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

@app.get("/api/diag")
async def diagnostics():
    return {
        "has_api_key": bool(PARALLEL_API_KEY),
        "api_key_length": len(PARALLEL_API_KEY) if PARALLEL_API_KEY else 0
    }

@app.get("/api/image-proxy")
async def image_proxy(url: str):
    """Proxy images to avoid CORS and hotlinking issues"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8"
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers, follow_redirects=True)
            response.raise_for_status()
            
            content_type = response.headers.get("content-type", "image/jpeg")
            
            return StreamingResponse(
                iter([response.content]),
                media_type=content_type,
                headers={
                    "Cache-Control": "public, max-age=86400",
                    "Access-Control-Allow-Origin": "*"
                }
            )
    except Exception as e:
        print(f"Image proxy failed for {url}: {str(e)}")
        raise HTTPException(status_code=404, detail="Image not found")
