"""Hassal Inc — Vercel Serverless Entry Point
South African M&A & Liquidity Event Monitor
"""

import os
import sys
import logging
from datetime import datetime

from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

# All modules are co-located in api/ for Vercel bundling
API_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, API_DIR)

from database import init_db, insert_deal, get_deals, get_deal_count, get_sources_summary, get_deal_types_summary
from scrapers import run_all_scrapers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("hassal_inc")

app = FastAPI(title="Hassal Inc", description="South African M&A & Liquidity Event Monitor")

TEMPLATE_DIR = os.path.join(API_DIR, "templates")
templates = Jinja2Templates(directory=TEMPLATE_DIR)

# Initialize DB on cold start
init_db()


def _run_scrape():
    """Run scrapers and store results."""
    deals = run_all_scrapers()
    new_count = 0
    for deal in deals:
        if insert_deal(deal):
            new_count += 1
    return new_count, len(deals)


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    deals = get_deals(limit=50)
    total = get_deal_count()
    sources = get_sources_summary()
    deal_types = get_deal_types_summary()
    return templates.TemplateResponse(
        name="dashboard.html",
        context={
            "request": request,
            "deals": deals,
            "total": total,
            "sources": sources,
            "deal_types": deal_types,
            "last_updated": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        },
    )


@app.get("/api/deals")
async def api_deals(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    source: str = Query(None),
    deal_type: str = Query(None),
    search: str = Query(None),
):
    deals = get_deals(limit=limit, offset=offset, source=source,
                      deal_type=deal_type, search=search)
    return {"deals": deals, "total": get_deal_count()}


@app.get("/api/sources")
async def api_sources():
    return {"sources": get_sources_summary()}


@app.get("/api/deal-types")
async def api_deal_types():
    return {"deal_types": get_deal_types_summary()}


@app.post("/api/scrape")
async def trigger_scrape():
    new_count, total_found = _run_scrape()
    return {"message": f"Scrape complete. {new_count} new deals found.", "total": get_deal_count()}


@app.get("/api/cron")
async def cron_scrape():
    """Endpoint for Vercel Cron Jobs to trigger periodic scrapes."""
    new_count, total_found = _run_scrape()
    return {"ok": True, "new_deals": new_count, "total_scanned": total_found}


@app.get("/about", response_class=HTMLResponse)
async def about(request: Request):
    return templates.TemplateResponse(
        name="about.html",
        context={"request": request},
    )
