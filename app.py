"""Hassal Inc — FastAPI Web Application
South African M&A & Liquidity Event Monitor
"""

import logging
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from apscheduler.schedulers.background import BackgroundScheduler

from database import init_db, insert_deal, get_deals, get_deal_count, get_sources_summary, get_deal_types_summary
from scrapers import run_all_scrapers
from config import CHECK_INTERVAL_MINUTES

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
)
logger = logging.getLogger("hassal_inc")

scheduler = BackgroundScheduler()


def scheduled_scrape():
    """Background job: scrape all sources and store new deals."""
    logger.info("Starting scheduled scrape...")
    deals = run_all_scrapers()
    new_count = 0
    for deal in deals:
        if insert_deal(deal):
            new_count += 1
    logger.info(f"Scrape complete. {new_count} new deals added out of {len(deals)} found.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    scheduled_scrape()  # initial scrape on startup
    scheduler.add_job(scheduled_scrape, "interval", minutes=CHECK_INTERVAL_MINUTES)
    scheduler.start()
    logger.info(f"Scheduler started — scraping every {CHECK_INTERVAL_MINUTES} minutes")
    yield
    scheduler.shutdown()


app = FastAPI(
    title="Hassal Inc",
    description="South African M&A & Liquidity Event Monitor",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


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
    """Manually trigger a scrape."""
    deals = run_all_scrapers()
    new_count = 0
    for deal in deals:
        if insert_deal(deal):
            new_count += 1
    return {"message": f"Scrape complete. {new_count} new deals found.", "total": get_deal_count()}


@app.get("/about", response_class=HTMLResponse)
async def about(request: Request):
    return templates.TemplateResponse(name="about.html", context={"request": request})
