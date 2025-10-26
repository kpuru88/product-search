# Quick Start Guide

Get the refactored product search backend running in 5 minutes.

## Prerequisites

- Python 3.9+
- pip
- Parallel AI API key

## Setup

### 1. Navigate to backend directory
```bash
cd /Users/karthikapurushothaman/projects/product-search/backend
```

### 2. Install dependencies
```bash
pip install fastapi uvicorn httpx openai python-dotenv pydantic
```

Or if you have a requirements.txt:
```bash
pip install -r requirements.txt
```

### 3. Create .env file
```bash
echo "PARALLEL_API_KEY=your_api_key_here" > .env
```

Replace `your_api_key_here` with your actual Parallel AI API key.

### 4. Run the server
```bash
# Option 1: Use the helper script
chmod +x scripts/run.sh
./scripts/run.sh

# Option 2: Direct uvicorn command
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Test it works
Open another terminal and run:
```bash
# Health check
curl http://localhost:8000/healthz

# Should return: {"status":"ok"}

# Diagnostics
curl http://localhost:8000/api/diag

# Should show API key info
```

## API Usage

### Chat Intake (Parse Query)
```bash
curl -X POST http://localhost:8000/api/chat/intake \
  -H "Content-Type: application/json" \
  -d '{"message": "black accent chair under $200"}'
```

### Product Search
```bash
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"message": "black accent chair"}'
```

### Image Proxy
```bash
curl "http://localhost:8000/api/image-proxy?url=https://example.com/image.jpg"
```

## API Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Testing

### Run unit tests
```bash
./scripts/test.sh
# Or: pytest -v tests/
```

### Run linting
```bash
./scripts/lint.sh
```

## Project Structure

```
backend/
├── app/
│   ├── api/              # API endpoints (routers)
│   ├── application/      # Business logic (services)
│   ├── domain/           # Data models (Pydantic)
│   ├── adapters/         # External API wrappers
│   ├── utils/            # Utilities and helpers
│   └── main.py           # App entry point
├── tests/                # Unit and integration tests
├── scripts/              # Helper scripts
├── README.md             # Full documentation
├── MIGRATION.md          # Migration guide from old code
├── QUICKSTART.md         # This file
└── pyproject.toml        # Tool configuration
```

## Common Issues

### ImportError: No module named 'fastapi'
**Solution**: Install dependencies with `pip install -r requirements.txt`

### ValueError: PARALLEL_API_KEY environment variable is required
**Solution**: Create `.env` file with your API key

### Port 8000 already in use
**Solution**: Use a different port: `uvicorn app.main:app --reload --port 8001`

### Module not found errors
**Solution**: Make sure you're in the `backend/` directory when running commands

## Next Steps

1. Read [README.md](README.md) for full architecture documentation
2. Check [MIGRATION.md](MIGRATION.md) if coming from old code
3. Explore the code in `app/` directory
4. Add your own tests in `tests/`
5. Extend functionality by adding new services

## Development Workflow

1. **Make changes** to code in `app/`
2. **Run tests**: `./scripts/test.sh`
3. **Check lint**: `./scripts/lint.sh`
4. **Test manually**: Use curl or Swagger UI
5. **Commit**: Once everything works

## Need Help?

- Check the [README.md](README.md) for detailed docs
- Look at existing code for examples
- Each module has docstrings explaining its purpose
- Tests show how to use utilities and services

## Example: Adding a New Feature

Let's say you want to add a new utility function:

1. **Create the function** in `app/utils/my_feature.py`:
```python
def my_new_function(input: str) -> str:
    """Do something useful."""
    return input.upper()
```

2. **Write a test** in `tests/test_utils_my_feature.py`:
```python
from app.utils.my_feature import my_new_function

def test_my_new_function():
    assert my_new_function("hello") == "HELLO"
```

3. **Run tests**: `pytest tests/test_utils_my_feature.py`

4. **Use it** in a service or router

That's it! The modular architecture makes it easy to add features.



