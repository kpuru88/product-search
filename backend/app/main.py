from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
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
        
        objective = f"""Find US ecommerce product purchase pages for: "{normalized_query}". 
Strictly prioritize PDPs from: {manufacturer_domains}, {retailer_domains}. 
Return URLs that display current price. Exclude forums/news/review-only pages. 
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
  "normalized_title": string,  // apply normalization rules: max 3 tokens (2-4 words), keep color and essential qualifiers, drop marketing filler
  "price": number | null,
  "currency": string | null,
  "availability": string | null,
  "model": string | null,
  "match_score": number,       // 0-1 vs normalized_query
  "review_snippets": string[], // <=10
  "images": [
    {{"url": string, "width": number|null, "height": number|null, "alt": string|null}}
  ],
  "primary_image_url": string | null
}}

Rules:
- Prefer gallery/hero images; fall back to og:image/twitter:image if available in content
- If multiple prices, pick the current new price; else null
- normalized_title should be max 3 tokens (2-4 words), e.g., "black accent chair"
- match_score should reflect how well this product matches "{normalized_query}"

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
        
        if "normalized_title" not in product_data or not product_data["normalized_title"]:
            if "title" in product_data:
                normalized = await normalize_name(product_data["title"])
                product_data["normalized_title"] = normalized.get("normalized_query", product_data["title"])
        
        return product_data
    
    except Exception as e:
        print(f"Product extraction failed for {url}: {str(e)}")
        return None

async def analyze_reviews(review_snippets: List[str], normalized_title: str = "") -> dict:
    if not review_snippets or len(review_snippets) == 0:
        return {
            "review_sentiment": "unknown",
            "sentiment_score": None,
            "fake_review_probability": None
        }
    
    try:
        async def call_sentiment():
            product_context = f"Product: {normalized_title}\n" if normalized_title else ""
            response = await client.chat.completions.create(
                model="speed",
                messages=[
                    {
                        "role": "system",
                        "content": "You evaluate product reviews and exclude likely fake content before summarizing sentiment."
                    },
                    {
                        "role": "user",
                        "content": f"""{product_context}SNIPPETS: {json.dumps(review_snippets[:10])}

Return ONLY JSON with these fields:
- review_sentiment: "positive" or "neutral" or "negative"
- sentiment_score: number 0-1
- fake_review_probability: number 0-1 (use high values when snippets are repetitive, bursty, templated, or generic)

If many snippets have fake_review_probability >0.7, ignore those and summarize sentiment from the remainder.

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
        except json.JSONDecodeError:
            return {
                "review_sentiment": "unknown",
                "sentiment_score": None,
                "fake_review_probability": None
            }
        
        return sentiment_data
    
    except Exception as e:
        print(f"Sentiment analysis failed: {str(e)}")
        return {
            "review_sentiment": "unknown",
            "sentiment_score": None,
            "fake_review_probability": None
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
            currency=product_data.get("currency", "USD"),
            url=url,
            source=source,
            match_score=product_data["match_score"],
            availability=product_data.get("availability"),
            review_sentiment=sentiment_data["review_sentiment"],
            sentiment_score=sentiment_data.get("sentiment_score"),
            fake_review_probability=sentiment_data.get("fake_review_probability"),
            primary_image_url=product_data.get("primary_image_url"),
            images=images
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
        
        tasks = [process_product(result, normalized_query) for result in search_results[:6]]
        products_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        products = [p for p in products_results if isinstance(p, ProductItem)]
        
        filtered_products = [p for p in products if p.match_score >= 0.35]
        
        filtered_products.sort(
            key=lambda p: (
                -p.match_score,
                -get_domain_tier(p.url),
                -(1 if p.price is not None else 0)
            )
        )
        
        return SearchResponse(query=normalized_query, items=filtered_products)
    
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
