from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.repositories.trends import (
    get_dashboard_summary,
    get_keyword_detail,
    get_keyword_news,
    get_keyword_series,
    get_latest_observations,
    get_recent_alerts,
)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    return Response(status_code=204)


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    observations = get_latest_observations(db)
    alerts = get_recent_alerts(db, limit=10)
    summary = get_dashboard_summary(db)
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "observations": observations,
            "alerts": alerts,
            "summary": summary,
        },
    )


@router.get("/keywords/{keyword_id}", response_class=HTMLResponse)
def keyword_detail_page(request: Request, keyword_id: int, db: Session = Depends(get_db)) -> HTMLResponse:
    keyword = get_keyword_detail(db, keyword_id)
    if keyword is None:
        raise HTTPException(status_code=404, detail="Keyword not found")
    series = get_keyword_series(db, keyword.normalized_text, days=7)
    chart_series = [
        {
            "captured_at": item["captured_at"].isoformat(),
            "source_rank": item["source_rank"],
            "source_value": item["source_value"],
        }
        for item in series
    ]
    news = get_keyword_news(db, keyword_id, limit=10)
    return templates.TemplateResponse(
        request,
        "keyword_detail.html",
        {
            "keyword": keyword,
            "series": chart_series,
            "news": news,
        },
    )


@router.get("/api/trends/latest")
def api_latest_trends(limit: int = Query(default=20, ge=1, le=100), db: Session = Depends(get_db)) -> list[dict]:
    observations = get_latest_observations(db, limit=limit)
    return [
        {
            "observation_id": obs.id,
            "keyword_id": obs.keyword_id,
            "keyword": obs.keyword.keyword_text,
            "rank": obs.source_rank,
            "source_value": obs.source_value,
            "captured_at": obs.captured_at,
        }
        for obs in observations
    ]


@router.get("/api/trends/series")
def api_keyword_series(keyword: str, days: int = Query(default=7, ge=1, le=30), db: Session = Depends(get_db)) -> list[dict]:
    return get_keyword_series(db, keyword, days)


@router.get("/api/alerts/recent")
def api_recent_alerts(limit: int = Query(default=20, ge=1, le=100), db: Session = Depends(get_db)) -> list[dict]:
    alerts = get_recent_alerts(db, limit=limit)
    return [
        {
            "id": alert.id,
            "keyword_id": alert.keyword_id,
            "keyword": alert.keyword.keyword_text,
            "reason": alert.trigger_reason,
            "triggered_at": alert.triggered_at,
            "notification_sent_at": alert.notification_sent_at,
        }
        for alert in alerts
    ]


@router.get("/api/keywords/{keyword_id}/news")
def api_keyword_news(keyword_id: int, limit: int = Query(default=10, ge=1, le=20), db: Session = Depends(get_db)) -> list[dict]:
    return [
        {
            "id": article.id,
            "title": article.title,
            "url": article.url,
            "publisher": article.publisher,
            "published_at": article.published_at,
        }
        for article in get_keyword_news(db, keyword_id, limit=limit)
    ]
