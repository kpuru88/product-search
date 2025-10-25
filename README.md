# Lost-Item Product Search & Discovery

A chat-first application for finding matching products based on lost-item descriptions, with sentiment analysis and fake review filtering powered by Parallel AI APIs.

## Features

- **Chat-based search interface**: Conversational UI for describing lost items
- **Intelligent product matching**: Uses Parallel Search API to find relevant products from manufacturer and retailer sites
- **Sentiment analysis**: Analyzes product reviews to determine sentiment (positive/neutral/negative)
- **Fake review detection**: Filters out likely fake reviews before computing sentiment scores
- **Match scoring**: Ranks products by relevance with visual match score indicators
- **Two-panel interface**: Conversation on the left, product results on the right

## Architecture

### Backend (FastAPI)
- **Chat Intake**: Extracts structured search intent from user messages
- **Search**: Calls Parallel Search API with composed objective
- **Product Extraction**: Parses product details (title, price, currency, availability, reviews)
- **Sentiment Analysis**: Evaluates review sentiment and detects fake reviews
- **Ranking**: Filters and sorts results by match score, merchant priority, and price freshness

### Frontend (React + TypeScript)
- **Vite** for fast development and building
- **Tailwind CSS** for styling
- **shadcn/ui** for pre-built components
- **Lucide React** for icons

## Setup Instructions

### Prerequisites
- Python 3.12+
- Node.js 18+
- Poetry (for Python dependency management)
- PARALLEL_API_KEY (get from https://parallel.ai)

### Backend Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. Install dependencies:
```bash
poetry install
```

3. Create a `.env` file with your Parallel API key:
```bash
echo "PARALLEL_API_KEY=your_api_key_here" > .env
```

4. Start the development server:
```bash
poetry run fastapi dev app/main.py
```

The backend will be available at http://localhost:8000

### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Create a `.env` file with the backend URL:
```bash
echo "VITE_API_URL=http://localhost:8000" > .env
```

4. Start the development server:
```bash
npm run dev
```

The frontend will be available at http://localhost:5173

## API Endpoints

### Health Check
```bash
GET /healthz
```

Returns: `{"status": "ok"}`

### Chat Intake
```bash
POST /api/chat/intake
Content-Type: application/json

{
  "message": "black leather couch"
}
```

Returns structured search intent with category, brand, model, specs, etc.

### Search
```bash
POST /api/search
Content-Type: application/json

{
  "message": "sony wh-1000xm5"
}
```

Returns product results with match scores, prices, sentiment analysis, and fake review probabilities.

## Example Requests

### Example 1: Specific Product
```bash
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"message": "sony wh-1000xm5"}'
```

### Example 2: Vague Description
```bash
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"message": "black leather couch"}'
```

### Example 3: With Specifications
```bash
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"message": "84-inch black leather sofa"}'
```

## Response Format

```json
{
  "query": "sony wh-1000xm5",
  "items": [
    {
      "title": "Sony WH-1000XM5 Premium Wireless Noise Canceling Headphones",
      "price": 299.99,
      "currency": "USD",
      "url": "https://electronics.sony.com/...",
      "source": "electronics.sony.com",
      "match_score": 1.0,
      "review_sentiment": "positive",
      "sentiment_score": 0.95,
      "fake_review_probability": 0.8,
      "availability": "In Stock"
    }
  ]
}
```

## Performance Notes

- **Search latency**: ~60 seconds per query due to Parallel API processing time
- **Rate limits**: 300 requests/minute for Chat API, 600 requests/minute for Search API
- **Retry logic**: Automatic retry with exponential backoff on 429/5xx errors (max 2 attempts)

## Deployment

### Backend Deployment
The backend is deployed at: https://app-eprtrlpk.fly.dev

**Important**: The deployed backend requires the PARALLEL_API_KEY environment variable to be set. The .env file is not automatically deployed. You need to set the environment variable manually in the deployment platform.

### Frontend Deployment
The frontend is deployed at: https://lost-item-search-app-nnv7wgsd.devinapps.com

The frontend is configured to use the deployed backend URL.

## Implementation Details

### 5-Step Flow (as per PRD)

1. **Chat Intake**: Parallel Chat API extracts structured intent (category, brand, model, specs, region, strictness)
2. **Search**: Parallel Search API finds ranked product URLs with LLM-optimized excerpts
3. **Product Extraction**: Parallel Chat API parses product details from page excerpts
4. **Sentiment & Fake Review**: Parallel Chat API analyzes reviews and detects fake content
5. **Ranking & Response**: Filters (match_score >= 0.35), sorts by match score → merchant priority → price freshness

### Merchant Priority
- **Tier 3** (highest): Manufacturer sites (Apple, Samsung, Sony, LG, Dell, HP)
- **Tier 2**: Major retailers (Amazon, Walmart, Target, Best Buy, Home Depot, Lowe's, IKEA, Wayfair, Ashley Furniture)
- **Tier 1**: Marketplaces (eBay, Etsy, Mercari)
- **Tier 0**: Other sources

### Fake Review Detection
Reviews with fake_review_probability > 0.7 are excluded from sentiment calculation. The system looks for:
- Repetitive/templated language
- Time-burst patterns
- Generic superlatives
- Profile anomalies

## Technology Stack

- **Backend**: FastAPI, Python 3.12, Poetry, OpenAI SDK (for Parallel Chat API), httpx
- **Frontend**: React, TypeScript, Vite, Tailwind CSS, shadcn/ui, Lucide React
- **APIs**: Parallel AI (Search, Chat, Extract)

## Development

### Running Tests
```bash
# Backend
cd backend
poetry run pytest

# Frontend
cd frontend
npm test
```

### Building for Production
```bash
# Backend
cd backend
poetry build

# Frontend
cd frontend
npm run build
```

## Troubleshooting

### Backend Issues
- **"PARALLEL_API_KEY environment variable is required"**: Make sure the .env file exists with your API key
- **Slow responses**: The Parallel API takes ~60 seconds per search - this is expected
- **429 errors**: You've hit the rate limit - wait a moment and try again

### Frontend Issues
- **"Search failed"**: Check that the backend is running and the VITE_API_URL is correct
- **CORS errors**: Make sure the backend CORS middleware is enabled (it should be by default)

## License

This project was built as a demonstration of the Parallel AI APIs for lost-item product search and discovery.

## Contact

For issues or questions about the Parallel AI APIs, visit https://docs.parallel.ai
