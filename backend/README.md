# Product Search Backend

AI-powered product search with sentiment analysis, built with FastAPI and Parallel AI.

## Architecture

This codebase follows a clean, layered architecture:

```
app/
├── api/                    # API layer (FastAPI routers)
│   ├── router_chat.py      # Chat intake endpoints
│   ├── router_search.py    # Search endpoints
│   ├── router_misc.py      # Health, diagnostics, image proxy
│   └── deps.py             # Shared dependencies
├── application/            # Application layer (use cases)
│   ├── chat_intake_service.py
│   ├── search_service.py
│   ├── extraction_service.py
│   └── review_service.py
├── domain/                 # Domain models (Pydantic schemas)
│   ├── intent.py
│   ├── product.py
│   └── chat.py
├── adapters/              # External API integrations
│   ├── parallel_chat.py
│   ├── parallel_search.py
│   ├── parallel_extract.py
│   └── http_fetch.py
├── utils/                 # Utilities
│   ├── config.py
│   ├── retry.py
│   ├── domains.py
│   ├── normalization.py
│   ├── classify.py
│   ├── expand.py
│   ├── price.py
│   ├── images.py
│   ├── ranking.py
│   └── logging.py
└── main.py               # FastAPI app factory
```

## Module Map

### API Layer (`app/api/`)
- **Purpose**: Handle HTTP requests/responses only
- **No business logic** - delegates to application services
- Routes map to services in the application layer

### Application Layer (`app/application/`)
- **Purpose**: Orchestrate use cases by composing adapters and utilities
- `chat_intake_service.py`: Parse user queries into structured intents
- `search_service.py`: End-to-end search pipeline orchestrator
- `extraction_service.py`: Extract product data from web pages
- `review_service.py`: Analyze sentiment and detect fake reviews

### Domain Layer (`app/domain/`)
- **Purpose**: Define data models and schemas
- Pure Pydantic models with no I/O or network calls
- Shared across all layers

### Adapters Layer (`app/adapters/`)
- **Purpose**: Wrap external APIs and services
- `parallel_chat.py`: Parallel AI chat/completions wrapper
- `parallel_search.py`: Parallel AI search wrapper
- `parallel_extract.py`: Parallel AI extract wrapper
- `http_fetch.py`: HTTP fetching for HTML and images

### Utils Layer (`app/utils/`)
- **Purpose**: Pure functions and helpers
- All functions are testable and reusable
- No direct API calls (use adapters for that)

## API Endpoints

- `POST /api/chat/intake` - Parse user query into structured intent
- `POST /api/search` - Execute complete product search
- `GET /healthz` - Health check
- `GET /api/diag` - Diagnostics and configuration check
- `GET /api/image-proxy?url=...` - Proxy images (CORS workaround)

## Development

### Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create `.env` file:
```bash
PARALLEL_API_KEY=your_api_key_here
```

### Running

```bash
# Development server with auto-reload
./scripts/run.sh

# Or manually:
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Testing

```bash
# Run all tests
./scripts/test.sh

# Or manually:
pytest -v tests/
```

### Linting

```bash
# Run linting and type checking
./scripts/lint.sh
```

## Configuration

All configuration is centralized in `app/utils/config.py`:
- API keys and base URLs
- Domain classifications (manufacturers, retailers, marketplaces)
- Timeouts and retry settings
- Search and ranking thresholds

## Adding Features

### Adding a new endpoint:
1. Add route in appropriate router (`app/api/router_*.py`)
2. Create/update service in `app/application/`
3. Add any new adapters/utilities as needed

### Adding a new external API:
1. Create adapter in `app/adapters/`
2. Use adapter in application services
3. Add configuration to `app/utils/config.py`

### Adding utilities:
1. Add pure function to appropriate utility module
2. Write unit tests in `tests/test_utils_*.py`
3. Import and use in services

## Design Principles

1. **Separation of Concerns**: Each layer has a clear responsibility
2. **Dependency Flow**: API → Application → Adapters/Utils
3. **Testability**: Pure functions in utils, mockable adapters
4. **Single Responsibility**: Small, focused modules (<300 LOC)
5. **DRY**: Shared utilities and configuration
6. **Type Safety**: Type hints on all public functions

## Behavioral Parity

This refactored codebase maintains **100% behavioral compatibility** with the original monolithic implementation:
- Same endpoints and JSON contracts
- Same filtering thresholds and ranking logic
- Same error messages and status codes
- Same image fallback and validation logic
- Same domain tier prioritization

## Dependencies

- FastAPI - Web framework
- Pydantic - Data validation
- httpx - HTTP client
- openai - OpenAI API client (used for Parallel AI)
- python-dotenv - Environment variable management



