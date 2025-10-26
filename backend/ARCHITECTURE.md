# Architecture Diagram

## Layer Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                         HTTP REQUEST                             │
│                   (POST /api/search)                             │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API LAYER (Routers)                         │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  router_search.py                                          │ │
│  │  - Validates request                                        │ │
│  │  - Calls application services                              │ │
│  │  - Returns response                                        │ │
│  └────────────────────────────────────────────────────────────┘ │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                  APPLICATION LAYER (Services)                    │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  ChatIntakeService                                          │ │
│  │  - Parses user query                                        │ │
│  │  - Extracts search intent                                  │ │
│  └────────────────────────────────────────────────────────────┘ │
│                           │                                      │
│                           ▼                                      │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  SearchService                                              │ │
│  │  - Orchestrates entire search flow                         │ │
│  │  - Composes: search → classify → extract → review → rank  │ │
│  └────────────────────────────────────────────────────────────┘ │
│           │                 │                  │                 │
│           ▼                 ▼                  ▼                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Extraction   │  │   Review     │  │   Utils      │          │
│  │   Service    │  │   Service    │  │  (ranking,   │          │
│  │              │  │              │  │   classify)  │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└──────────┬─────────────────┬─────────────────┬──────────────────┘
           │                 │                 │
           ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                   ADAPTERS LAYER (External APIs)                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Parallel     │  │ Parallel     │  │ Parallel     │          │
│  │ Chat Client  │  │Search Client │  │Extract Client│          │
│  │              │  │              │  │              │          │
│  │ - Wraps      │  │ - Wraps      │  │ - Wraps      │          │
│  │   AsyncOpenAI│  │   search API │  │   extract API│          │
│  │ - Handles    │  │ - Builds     │  │ - Gets page  │          │
│  │   retries    │  │   objectives │  │   content    │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└──────────┬─────────────────┬─────────────────┬──────────────────┘
           │                 │                 │
           ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                     EXTERNAL SERVICES                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Parallel AI  │  │ Parallel AI  │  │  Web Pages   │          │
│  │    Chat      │  │   Search     │  │   (HTML)     │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow Example: Search Request

```
1. USER → POST /api/search {"message": "black accent chair"}
   └─> router_search.py

2. router_search.py → ChatIntakeService.process_intake()
   └─> Calls ParallelChatClient
       └─> Returns SearchIntent(query_text="black accent chair", ...)

3. router_search.py → SearchService.search(intent, normalized_query)
   
4. SearchService orchestrates:
   
   a) Search for products
      └─> ParallelSearchClient.search(objective)
          └─> Returns URLs and excerpts
   
   b) Classify each URL
      └─> fetch_html(url) via http_fetch.py
      └─> classify_page(url, html) via classify.py
          └─> Returns "pdp" or "listing" or "homepage"
   
   c) Expand listings
      └─> expand_listing(url, html) via expand.py
          └─> Returns individual product URLs
   
   d) Extract product details (parallel)
      └─> ExtractionService.extract_product_details()
          ├─> Calls ParallelChatClient (LLM extraction)
          ├─> Calls ParallelExtractClient (images)
          ├─> Calls images.validate_image()
          └─> Calls price.extract_price_range()
          └─> Returns product data dict
   
   e) Analyze reviews (parallel)
      └─> ReviewService.analyze_reviews()
          └─> Calls ParallelChatClient (sentiment analysis)
          └─> Returns sentiment data
   
   f) Build ProductItem objects
      └─> Combines extraction + sentiment data
   
   g) Filter, deduplicate, rank
      └─> ranking.filter_by_match_score()
      └─> ranking.deduplicate_products()
      └─> ranking.rank_products()

5. SearchService → Returns SearchResponse(query, items)

6. router_search.py → Returns JSON response to client

7. USER ← Receives product results
```

## Module Dependencies

```
api/
├── router_chat.py
│   ├── depends on: application/chat_intake_service.py
│   └── returns: domain/chat.py (ChatIntakeResponse)
│
├── router_search.py
│   ├── depends on: application/chat_intake_service.py
│   ├── depends on: application/search_service.py
│   └── returns: domain/product.py (SearchResponse)
│
└── router_misc.py
    └── depends on: adapters/http_fetch.py

application/
├── chat_intake_service.py
│   ├── depends on: adapters/parallel_chat.py
│   ├── depends on: utils/normalization.py
│   └── returns: domain/intent.py (SearchIntent)
│
├── search_service.py
│   ├── depends on: adapters/parallel_search.py
│   ├── depends on: adapters/http_fetch.py
│   ├── depends on: application/extraction_service.py
│   ├── depends on: application/review_service.py
│   ├── depends on: utils/classify.py
│   ├── depends on: utils/expand.py
│   ├── depends on: utils/ranking.py
│   └── returns: domain/product.py (SearchResponse)
│
├── extraction_service.py
│   ├── depends on: adapters/parallel_chat.py
│   ├── depends on: adapters/parallel_extract.py
│   ├── depends on: utils/domains.py
│   ├── depends on: utils/classify.py
│   ├── depends on: utils/normalization.py
│   ├── depends on: utils/images.py
│   └── depends on: utils/price.py
│
└── review_service.py
    └── depends on: adapters/parallel_chat.py

domain/
├── intent.py (no dependencies)
├── product.py (no dependencies)
└── chat.py (depends on: domain/intent.py)

adapters/
├── parallel_chat.py
│   └── depends on: utils/config.py, utils/retry.py
│
├── parallel_search.py
│   └── depends on: utils/config.py, utils/retry.py
│
├── parallel_extract.py
│   └── depends on: utils/config.py
│
└── http_fetch.py
    └── depends on: utils/config.py

utils/
├── config.py (no dependencies)
├── retry.py (no dependencies)
├── domains.py (depends on: config.py)
├── normalization.py (no dependencies)
├── classify.py (no dependencies)
├── expand.py (no dependencies)
├── price.py (no dependencies)
├── images.py (depends on: config.py)
├── ranking.py (depends on: config.py, domains.py)
└── logging.py (no dependencies)
```

## Dependency Rules

1. **API layer** can depend on:
   - Application layer (services)
   - Domain layer (models)
   - ❌ Never on adapters or utils directly

2. **Application layer** can depend on:
   - Adapters layer (external APIs)
   - Utils layer (helpers)
   - Domain layer (models)
   - ❌ Never on API layer

3. **Domain layer** can depend on:
   - Other domain models only
   - ❌ Never on any other layer

4. **Adapters layer** can depend on:
   - Utils layer (config, retry)
   - ❌ Never on API, Application, or Domain

5. **Utils layer** can depend on:
   - Other utils only
   - ❌ Never on any higher layer

## Key Design Patterns

### 1. Dependency Injection
```python
# api/deps.py provides singleton instances
def get_search_service() -> SearchService:
    return SearchService(
        get_search_client(),
        get_extraction_service(),
        get_review_service()
    )
```

### 2. Service Layer Pattern
```python
# Services orchestrate use cases
class SearchService:
    def __init__(self, search_client, extraction_service, review_service):
        self.search_client = search_client
        self.extraction_service = extraction_service
        self.review_service = review_service
    
    async def search(self, intent, query):
        # Orchestrate the complete flow
        ...
```

### 3. Adapter Pattern
```python
# Adapters wrap external APIs
class ParallelChatClient:
    def __init__(self):
        self.client = AsyncOpenAI(...)
    
    async def create_completion(self, messages, ...):
        # Wraps OpenAI client with retries
        ...
```

### 4. Pure Functions
```python
# Utils are pure, testable functions
def get_domain_tier(url: str) -> int:
    # No side effects, easy to test
    domain = urlparse(url).netloc
    if manufacturer in domain: return 3
    ...
```

## Testing Strategy

```
Unit Tests (utils/)
├── test_utils_domains.py
├── test_utils_ranking.py
└── ... (pure functions, no mocking needed)

Integration Tests (application/)
├── test_chat_intake_service.py (mock adapters)
├── test_extraction_service.py (mock adapters)
└── ... (test services with mocked dependencies)

API Tests (api/)
├── test_api_chat.py (mock services)
├── test_api_search.py (mock services)
└── ... (test endpoints with mocked services)

E2E Tests
└── test_e2e_search_flow.py (real API calls, slow)
```

## Configuration Flow

```
1. Environment Variables (.env)
   └─> PARALLEL_API_KEY

2. utils/config.py
   └─> Loads env vars
   └─> Defines constants
   └─> Exports configuration

3. Adapters
   └─> Import from config
   └─> Use API keys, base URLs

4. Services
   └─> Import config for thresholds
   └─> Use max_results, timeouts

5. Utils
   └─> Import config for constants
   └─> Use domain lists, thresholds
```

## Error Handling Flow

```
1. External API Error
   └─> Adapter catches exception
       └─> Retries with backoff (retry.py)
       └─> If still fails, returns None or raises

2. Service Error
   └─> Service logs error
       └─> Returns graceful fallback
       └─> Or propagates to router

3. Router Error
   └─> Router catches exception
       └─> Converts to HTTPException
       └─> Returns error JSON to client

4. Client receives
   └─> Status code + error message
```

This architecture ensures:
- ✅ Clear separation of concerns
- ✅ Easy to test at each layer
- ✅ Easy to extend with new features
- ✅ Maintainable and understandable code



