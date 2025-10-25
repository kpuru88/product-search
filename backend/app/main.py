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

class ProductItem(BaseModel):
    title: str
    price: Optional[float] = None
    currency: str = "USD"
    url: str
    source: str
    match_score: float
    review_sentiment: Literal["positive", "neutral", "negative", "unknown"] = "unknown"
    sentiment_score: Optional[float] = None
    fake_review_probability: Optional[float] = None
    availability: Optional[str] = None

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
        
        return ChatIntakeResponse(intent=intent)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat intake failed: {str(e)}")

async def search_products(intent: SearchIntent) -> List[dict]:
    try:
        hints = []
        if intent.brand:
            hints.append(f"brand:{intent.brand}")
        if intent.model:
            hints.append(f"model:{intent.model}")
        if intent.core_specs:
            hints.append(f"specs:{','.join(intent.core_specs)}")
        
        hints_str = " ".join(hints) if hints else ""
        objective = f"Find live product pages matching: {intent.query_text} with hints {hints_str}. Prefer manufacturer and major retailer PDPs in the US that show current price. Exclude forums/news."
        
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
        return search_result.get("results", [])
    
    except Exception as e:
        print(f"Search failed: {str(e)}")
        return []

async def extract_product_details(url: str, excerpts: List[str], query_text: str) -> Optional[dict]:
    try:
        excerpt_text = " ".join(excerpts[:3]) if excerpts else ""
        
        async def call_extract():
            response = await client.chat.completions.create(
                model="speed",
                messages=[
                    {
                        "role": "system",
                        "content": "You extract product details from retailer/manufacturer pages and return strict JSON."
                    },
                    {
                        "role": "user",
                        "content": f"""User query: {query_text}
URL: {url}
CONTENT: {excerpt_text[:3000]}

Extract and return ONLY JSON with these fields:
- title (string)
- price (number or null)
- currency (string, ISO code)
- model (string or null)
- availability (string or null)
- review_snippets (array of strings, up to 10 short quotes)
- match_score (number 0-1 for how well this product matches the user query)

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
        
        return product_data
    
    except Exception as e:
        print(f"Product extraction failed for {url}: {str(e)}")
        return None

async def analyze_reviews(review_snippets: List[str]) -> dict:
    if not review_snippets or len(review_snippets) == 0:
        return {
            "review_sentiment": "unknown",
            "sentiment_score": None,
            "fake_review_probability": None
        }
    
    try:
        async def call_sentiment():
            response = await client.chat.completions.create(
                model="speed",
                messages=[
                    {
                        "role": "system",
                        "content": "You evaluate product reviews and identify likely fake/astroturfed content. Return JSON only."
                    },
                    {
                        "role": "user",
                        "content": f"""Given these review_snippets, return ONLY JSON with these fields:
- review_sentiment: "positive" or "neutral" or "negative"
- sentiment_score: number 0-1
- fake_review_probability: number 0-1 (use high values when snippets are repetitive, bursty, templated, or generic)

If many snippets have fake_review_probability >0.7, ignore those and summarize sentiment from the remainder.

Review snippets: {json.dumps(review_snippets[:10])}

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

async def process_product(result: dict, query_text: str) -> Optional[ProductItem]:
    try:
        url = result.get("url", "")
        excerpts = result.get("excerpts", [])
        
        if not url:
            return None
        
        product_data = await extract_product_details(url, excerpts, query_text)
        
        if not product_data:
            return None
        
        review_snippets = product_data.get("review_snippets", [])
        sentiment_data = await analyze_reviews(review_snippets)
        
        from urllib.parse import urlparse
        source = urlparse(url).netloc.replace("www.", "")
        
        product = ProductItem(
            title=product_data["title"],
            price=product_data.get("price"),
            currency=product_data.get("currency", "USD"),
            url=url,
            source=source,
            match_score=product_data["match_score"],
            availability=product_data.get("availability"),
            review_sentiment=sentiment_data["review_sentiment"],
            sentiment_score=sentiment_data.get("sentiment_score"),
            fake_review_probability=sentiment_data.get("fake_review_probability")
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
        
        search_results = await search_products(intent)
        
        if not search_results:
            return SearchResponse(query=intent.query_text, items=[])
        
        tasks = [process_product(result, intent.query_text) for result in search_results[:6]]
        products_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        products = [p for p in products_results if isinstance(p, ProductItem)]
        
        filtered_products = [p for p in products if p.match_score >= 0.35]
        
        def merchant_priority(source: str) -> int:
            source_lower = source.lower()
            if any(brand in source_lower for brand in ["apple", "samsung", "sony", "lg", "dell", "hp"]):
                return 3
            if any(retailer in source_lower for retailer in ["amazon", "walmart", "target", "bestbuy", "homedepot", "lowes", "ikea", "wayfair", "ashleyfurniture"]):
                return 2
            if any(market in source_lower for market in ["ebay", "etsy", "mercari"]):
                return 1
            return 0
        
        filtered_products.sort(
            key=lambda p: (
                -p.match_score,
                -merchant_priority(p.source),
                -(1 if p.price is not None else 0)
            )
        )
        
        return SearchResponse(query=intent.query_text, items=filtered_products)
    
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
