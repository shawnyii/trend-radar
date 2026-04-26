# Trend Radar MVP Plan

## Overview

Trend Radar is a personal-use trend monitoring tool focused on Taiwan trending keywords. The MVP collects Google Trends Taiwan keywords on a schedule, stores timestamped history in PostgreSQL, detects sudden spikes with simple rules, pushes alerts and daily summaries to Discord, and exposes a small dashboard for browsing recent and historical movement plus related news links.

## MVP Scope

- Collect from one source only: Google Trends Taiwan
- Store every fetch result with timestamps
- Detect spike alerts with simple rules
- Send one daily summary to Discord
- Send extra Discord alerts for spikes
- Show latest trends, keyword history, alerts, and news links in the dashboard
- Enrich each keyword with a small number of Google News RSS links

## Non-Goals

- No user accounts or auth
- No multi-source ingestion
- No keyword grouping or synonym mapping
- No AI summarization
- No CSV export
- No admin console

## Architecture

### API / Dashboard

- FastAPI app serves JSON APIs and HTML dashboard pages
- Jinja templates render dashboard views
- Chart.js renders keyword history on the detail page

### ETL / Workers

- APScheduler runs hourly collection
- Collection job:
  1. fetch Google Trends RSS
  2. write snapshot + observations
  3. fetch Google News RSS per keyword
  4. detect spikes
  5. send Discord alerts
- Daily summary job sends the latest top keywords once per day

### Storage

- PostgreSQL is the target runtime database
- SQLAlchemy models represent snapshots, keywords, observations, news, alerts, and job runs
- Alembic migration tracks schema creation

## Main Modules

- `app/core`: settings, DB engine, shared app config
- `app/models`: SQLAlchemy entities
- `app/repositories`: read-query helpers for API and dashboard
- `app/services/trends.py`: Google Trends adapter and normalization
- `app/services/ingest.py`: persistence flow
- `app/services/news.py`: Google News RSS enrichment
- `app/services/spike_detection.py`: alert rule logic
- `app/services/notifications.py`: Discord payloads and send logic
- `app/workers/jobs.py`: orchestration jobs
- `app/api/routes.py`: API and HTML routes

## Data Model

### `trend_snapshots`

- one record per collection batch
- fields: source, captured_at, status, raw_count

### `keywords`

- canonical keyword row
- fields: keyword_text, normalized_text, first_seen_at, last_seen_at

### `trend_observations`

- one row per keyword per snapshot
- fields: rank, source_value, captured_at

### `news_articles`

- up to a few RSS articles per keyword
- fields: title, url, publisher, published_at, fetched_at

### `alerts`

- one row per spike event
- fields: trigger_reason, baseline_value, current_value, dedupe_key, triggered_at

### `job_runs`

- operational log for collection and summary jobs

## External Integrations

### Google Trends Taiwan

- fetched through RSS adapter
- wrapped in custom service to keep replacement cost low

### Google News RSS

- queried per keyword
- stores metadata only, not full articles

### Discord Incoming Webhook

- used for daily summary and spike alerts
- no bot token or gateway connection

## API Surface

- `GET /health`
- `GET /`
- `GET /keywords/{keyword_id}`
- `GET /api/trends/latest`
- `GET /api/trends/series?keyword=...&days=7`
- `GET /api/alerts/recent`
- `GET /api/keywords/{keyword_id}/news`

## Spike Rules

- New keyword that enters top rank threshold
- Large rank jump compared with recent average
- Sustained high rank across recent observations

Alerts are deduplicated within a fixed time window.

## Delivery Plan

### Phase 1

- project bootstrap
- settings and DB wiring
- documentation and Docker scaffold

### Phase 2

- schema and migration
- trends adapter
- ingest pipeline

### Phase 3

- news enrichment
- spike detection
- Discord notification flow

### Phase 4

- API routes
- dashboard templates
- Chart.js history view

### Phase 5

- tests
- README polish
- GitHub-ready repo structure

## Test Plan

- unit test spike rule generation
- integration test latest trends API
- verify DB schema creates successfully
- verify collection pipeline handles missing webhook config

## Defaults

- Timezone: `Asia/Taipei`
- Collection interval: every 60 minutes
- Daily summary: 01:52
- Dashboard auth: none
- Deployment target: single Docker VM
