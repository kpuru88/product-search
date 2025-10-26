# Migration Guide: Refactored Architecture

This document explains the refactoring from a monolithic `main.py` to a layered architecture.

## What Changed

### Before
- Single `main.py` file with 1089 lines
- All code (models, services, utilities, routes) in one file
- Difficult to test, maintain, and extend

### After
- Modular architecture with clear separation of concerns
- 30+ focused modules, each <300 lines
- Easy to test, maintain, and extend
- Same behavior and API contracts

## File Mapping

### Models
**Before**: Classes in `main.py`
**After**: Organized in `app/domain/`

- `SearchIntent` → `app/domain/intent.py`
- `ProductItem`, `Image`, `SearchResponse` → `app/domain/product.py`
- `ChatRequest`, `ChatIntakeResponse` → `app/domain/chat.py`

### API Endpoints
**Before**: Route decorators in `main.py`
**After**: Organized in `app/api/router_*.py`

- `@app.post("/api/chat/intake")` → `app/api/router_chat.py`
- `@app.post("/api/search")` → `app/api/router_search.py`
- `@app.get("/healthz")`, `/api/diag`, `/api/image-proxy` → `app/api/router_misc.py`

### Business Logic Functions
**Before**: Functions in `main.py`
**After**: Organized by responsibility

| Old Function | New Location |
|--------------|-------------|
| `retry_with_backoff()` | `app/utils/retry.py` |
| `get_domain_tier()`, `is_ecommerce_domain()` | `app/utils/domains.py` |
| `normalize_name()` | `app/utils/normalization.py` |
| `validate_image()`, `get_page_media()` | `app/utils/images.py` |
| `fetch_html()` | `app/adapters/http_fetch.py` |
| `classify_page()`, `detect_listing_page()` | `app/utils/classify.py` |
| `expand_listing()` | `app/utils/expand.py` |
| `extract_price_range()` | `app/utils/price.py` |
| `search_products()` | `app/application/search_service.py` |
| `extract_product_details()` | `app/application/extraction_service.py` |
| `analyze_reviews()` | `app/application/review_service.py` |
| `chat_intake()` | `app/application/chat_intake_service.py` |
| Filter/rank logic | `app/utils/ranking.py` |

### Constants and Configuration
**Before**: Module-level variables in `main.py`
**After**: `app/utils/config.py`

- `PARALLEL_API_KEY`
- `MANUFACTURER_DOMAINS`, `MAJOR_RETAILERS`, `MARKETPLACES`
- Timeouts, thresholds, limits

### External API Clients
**Before**: Inline `httpx` and `AsyncOpenAI` calls
**After**: Wrapped in adapters

- `AsyncOpenAI` → `app/adapters/parallel_chat.py` (`ParallelChatClient`)
- Search API → `app/adapters/parallel_search.py` (`ParallelSearchClient`)
- Extract API → `app/adapters/parallel_extract.py` (`ParallelExtractClient`)
- HTTP fetch → `app/adapters/http_fetch.py`

## Import Changes

### Old imports (from main.py):
```python
from main import SearchIntent, ProductItem, ChatRequest
```

### New imports:
```python
from app.domain.intent import SearchIntent
from app.domain.product import ProductItem
from app.domain.chat import ChatRequest
```

## Running the Application

### Before:
```bash
uvicorn main:app --reload
```

### After:
```bash
# Option 1: Use the script
./scripts/run.sh

# Option 2: Manual
uvicorn app.main:app --reload

# Option 3: From project root
cd backend && uvicorn app.main:app --reload
```

## Testing

### Before:
- No tests provided

### After:
```bash
# Run tests
./scripts/test.sh

# Or manually
pytest -v tests/
```

## Environment Variables

**No changes** - still uses `.env` file with `PARALLEL_API_KEY`

## API Endpoints

**No changes** - all endpoints remain the same:
- `POST /api/chat/intake`
- `POST /api/search`
- `GET /healthz`
- `GET /api/diag`
- `GET /api/image-proxy?url=...`

## Behavioral Guarantees

The refactored code maintains **100% behavioral compatibility**:

1. ✅ Same endpoint URLs and methods
2. ✅ Same request/response JSON schemas
3. ✅ Same filtering thresholds (match_score >= 0.35)
4. ✅ Same ranking logic (match score → category → tier → price)
5. ✅ Same domain tier priorities
6. ✅ Same image validation and fallback logic
7. ✅ Same price range extraction for listings
8. ✅ Same error messages and HTTP status codes
9. ✅ Same retry logic with exponential backoff
10. ✅ Same normalization rules

## Extension Points

### Adding a new endpoint:
1. Create route in `app/api/router_*.py`
2. Add business logic in `app/application/`
3. Use existing adapters or create new ones

### Adding a new feature:
1. Add model to `app/domain/` if needed
2. Create service in `app/application/`
3. Add utilities in `app/utils/`
4. Wire up in router

### Adding tests:
1. Unit tests for utils: `tests/test_utils_*.py`
2. Integration tests for services: `tests/test_application_*.py`
3. API tests: `tests/test_api_*.py`

## Troubleshooting

### Import errors:
- Make sure you're running from the `backend/` directory
- Check that all `__init__.py` files exist
- Verify PYTHONPATH includes the backend directory

### Module not found:
```bash
# Set PYTHONPATH
export PYTHONPATH=/Users/karthikapurushothaman/projects/product-search/backend:$PYTHONPATH
```

### Missing dependencies:
```bash
pip install -r requirements.txt
```

## Benefits of New Architecture

1. **Modularity**: Each module has a single, clear purpose
2. **Testability**: Pure functions and mockable adapters
3. **Maintainability**: Small files, clear boundaries
4. **Extensibility**: Easy to add new features
5. **Type Safety**: Better IDE support and type checking
6. **Documentation**: Clear module structure and docstrings
7. **Debugging**: Easier to trace issues through layers
8. **Collaboration**: Multiple developers can work on different modules

## Questions?

If you encounter issues:
1. Check this migration guide
2. Review the README.md
3. Look at the module you're trying to use
4. Check tests for usage examples



