# Portfolio Analytics API

FastAPI service for your MongoDB portfolio snapshots. It calculates price per share, SMA trend, RSI, momentum, drawdown, portfolio weight, reference return, heuristic score, and watch signal.

> Signals are rule-based indicators over your own stored history. They are not predictions or investment advice.

## 1. Expected MongoDB document shape

Collection documents should look like:

```json
{
  "date": "2026-11-12",
  "data": [
    {
      "company": "Suzlon Energy",
      "shares": 11,
      "currentValue": 427.90,
      "referenceValue": 380.16
    }
  ]
}
```

`date` should be consistently stored as `YYYY-MM-DD` strings (or use a consistent BSON date strategy and adapt query bounds). Each `data` item needs `company`, `shares`, and `currentValue`. `referenceValue` is optional; `vs_reference` is null if missing or zero.

## 2. Run locally

Python 3.11+ recommended.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env and set MONGO_URI, database and collection names.
uvicorn main:app --reload
```

Open:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- Health: `http://localhost:8000/health`

## 3. Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Service metadata |
| GET | `/health` | Database health |
| GET | `/api/health` | API health |
| GET | `/api/portfolio/analyse` | Full company analysis and portfolio summary |
| GET | `/api/portfolio/summary` | Portfolio totals and signal counts |
| GET | `/api/portfolio/signals` | Filter by `BUY-WATCH`, `SELL-WATCH`, or `HOLD` |
| GET | `/api/portfolio/company/{company}` | One company's current analysis |
| GET | `/api/portfolio/company/{company}/history` | Historical price-per-share series |
| GET | `/api/portfolio/config` | Active indicator configuration |

Optional query parameters for analysis/history:
- `start_date=2026-11-01`
- `end_date=2026-11-17`
- `limit=5000` (1–20,000)

Examples:

```bash
curl http://localhost:8000/api/portfolio/analyse
curl "http://localhost:8000/api/portfolio/analyse?start_date=2026-11-01&end_date=2026-11-17"
curl "http://localhost:8000/api/portfolio/signals?signal=BUY-WATCH"
curl "http://localhost:8000/api/portfolio/company/Suzlon%20Energy"
curl "http://localhost:8000/api/portfolio/company/Suzlon%20Energy/history"
curl http://localhost:8000/api/portfolio/config
```

If `API_KEY` is configured, send:

```bash
curl -H "X-API-Key: YOUR_SECRET" http://localhost:8000/api/portfolio/analyse
```

## 4. Free deployment (Render + MongoDB Atlas)

1. Push this project to a GitHub repository.
2. Create a free MongoDB Atlas cluster (if you do not already have one).
3. In Atlas, create a database user, configure Network Access, and copy the application connection string. For production, restrict network access where possible; avoid permanently allowing all IPs unless your provider's outbound IP constraints require it and you understand the exposure.
4. In Render, create a **Web Service** from the GitHub repository and select the Docker runtime, or use the included `render.yaml` Blueprint.
5. Set `MONGO_URI`, `MONGO_DB_NAME`, `MONGO_COLLECTION_NAME`, and a strong `API_KEY` in Render environment variables.
6. Deploy. Render injects `PORT`; the Docker command uses it.
7. Test `/health`, then `/docs`.

Free hosting commonly sleeps or has usage/resource limits. The first request after inactivity may be slow, and free plans are not suitable for guaranteed uptime or production-critical workloads. Verify current provider limits before deployment.

## 5. Docker locally

```bash
docker build -t portfolio-analytics-api .
docker run --rm -p 8000:8000 --env-file .env portfolio-analytics-api
```

## 6. Performance and correctness notes

- Uses one application-lifetime Motor client with connection pooling; closes it on shutdown.
- Creates an ascending `date` index at startup.
- Uses MongoDB projection to fetch only `date` and `data`.
- Applies date filtering and a hard maximum document limit to bound memory use.
- Uses async MongoDB I/O. Indicator calculations are CPU-light for normal portfolio sizes.
- `build_series` assumes MongoDB returns documents in ascending date order.
- RSI intentionally uses the same simple-average gain/loss method as your submitted code, not Wilder's smoothed RSI. If there are no gains and no losses, RSI returns 50; if gains exist and losses are zero, it returns 100.
- The API's `limit` is a cap on the number of snapshots considered, not pagination. For long histories, request an appropriate date range.
- MongoDB dates are expected to be consistently stored as ISO date strings so lexical sorting and range queries work chronologically.

## 7. Security

- API is read-only (GET endpoints only).
- Set `API_KEY` to require an `X-API-Key` header on analytics endpoints.
- Do not commit `.env`, MongoDB credentials, or API keys.
- Configure CORS only for your actual frontend origin(s).
- Do not expose MongoDB directly to browsers.

## 8. Error behavior

FastAPI returns standard HTTP errors:
- `401`: missing/invalid API key when enabled
- `404`: company not found
- `422`: invalid date, date range, signal, or query parameter
- `500`: unexpected application/database failure (details are not exposed by default)

Swagger docs are generated from route and schema definitions.
