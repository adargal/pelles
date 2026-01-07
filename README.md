# Pelles - Shopping List Price Comparison

Compare shopping list prices across Israeli supermarkets (Shufersal & Super Hefer Large).

## Features

- Search-only scraping (no full catalog indexing)
- Hebrew text support
- Automatic product matching with confidence scores
- User can override matches
- Cheapest store recommendation

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy, Playwright
- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS
- **Database**: SQLite

## Setup

### Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Run the server
uvicorn app.main:app --reload
```

The API will be available at http://localhost:8000

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

The frontend will be available at http://localhost:5173

## API Endpoints

### POST /api/compare
Compare prices for a shopping list.

Request:
```json
{
  "items": ["חלב", "לחם", "ביצים"]
}
```

### POST /api/compare/{comparison_id}/override
Override a product selection.

Request:
```json
{
  "item_query": "חלב",
  "store_id": "shufersal",
  "product_id": "shufersal_12345"
}
```

### GET /api/stores
List available stores.

### GET /health
Health check endpoint.

## Configuration

Environment variables (optional):

| Variable | Default | Description |
|----------|---------|-------------|
| DATABASE_URL | sqlite+aiosqlite:///./pelles.db | Database connection string |
| CACHE_TTL_DAYS | 7 | Cache expiration in days |
| SCRAPER_DELAY_SECONDS | 1.5 | Delay between scrape requests |
| SCRAPER_MAX_RESULTS | 10 | Max products per search |
| MATCH_HIGH_THRESHOLD | 0.85 | Score threshold for high confidence |
| MATCH_MEDIUM_THRESHOLD | 0.60 | Score threshold for medium confidence |
| MIN_COVERAGE_FOR_RECOMMENDATION | 0.70 | Min coverage to recommend a store |

## Project Structure

```
pelles/
├── backend/
│   ├── app/
│   │   ├── api/          # API routes
│   │   ├── models/       # SQLAlchemy models
│   │   ├── schemas/      # Pydantic schemas
│   │   ├── scrapers/     # Store scrapers
│   │   ├── services/     # Business logic
│   │   ├── config.py     # Settings
│   │   ├── database.py   # DB setup
│   │   └── main.py       # FastAPI app
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/          # API client
│   │   ├── components/   # React components
│   │   ├── hooks/        # Custom hooks
│   │   ├── types/        # TypeScript types
│   │   └── App.tsx
│   └── package.json
└── README.md
```

## Limitations

- Prices are indicative and may change
- Data refreshes weekly (configurable)
- No user accounts or saved lists
- No multi-store basket optimization
- No branch-specific pricing

## License

MIT
