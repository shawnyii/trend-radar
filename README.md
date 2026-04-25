# Trend Radar

Trend Radar is a personal MVP for monitoring trending keywords in Taiwan. It collects Google Trends topics on a schedule, stores historical observations, detects simple spikes, enriches keywords with Google News RSS links, sends Discord notifications, and serves a lightweight dashboard.

## Stack

- Python 3.11+
- FastAPI
- SQLAlchemy + PostgreSQL
- APScheduler
- Discord incoming webhooks
- Chart.js

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
.venv/bin/python -m app.cli init-db
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`.

By default, `.env.example` uses local SQLite so the app can boot immediately without PostgreSQL.

## Docker

```bash
docker compose up --build
```

The Docker stack uses PostgreSQL through the `docker-compose.yml` environment overrides.

## Manual Jobs

```bash
.venv/bin/python -m app.cli init-db
.venv/bin/python -m app.cli collect-now
.venv/bin/python -m app.cli send-summary
```

Use `collect-now` before a demo to fetch fresh data without waiting for the scheduler.

## Main Endpoints

- `GET /`
- `GET /health`
- `GET /api/trends/latest`
- `GET /api/trends/series?keyword=ai&days=7`
- `GET /api/alerts/recent`
- `GET /api/keywords/{id}/news`

## Notes

- The Google Trends source is wrapped behind a custom adapter because there is no stable official Python API for this data.
- Spike detection uses simple rule-based logic for MVP scope only.
- If `DISCORD_WEBHOOK_URL` is empty, alerts and daily summary jobs are skipped gracefully.
