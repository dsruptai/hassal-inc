"""Hassal Inc — Scrapers for South African M&A / liquidity event sources"""

import re
import logging
from datetime import datetime, timedelta

import feedparser
import requests
from bs4 import BeautifulSoup
from dateutil import parser as date_parser

from config import DEAL_KEYWORDS, SA_KEYWORDS, SOURCES, MAX_ARTICLE_AGE_DAYS

logger = logging.getLogger("hassal_inc")

HEADERS = {
    "User-Agent": "HassalInc/1.0 (SA M&A Monitor; contact@hassalinc.co.za)"
}


def classify_deal_type(text: str) -> str:
    text_lower = text.lower()
    type_map = [
        (["acquisition", "acquired", "acquire", "buyout", "buy-out", "bought"], "Acquisition"),
        (["merger", "merge", "merged", "scheme of arrangement"], "Merger"),
        (["delisting", "delist", "delisted"], "Delisting"),
        (["disposal", "disposed", "divest", "divestiture", "unbundling"], "Disposal/Divestiture"),
        (["stake sale", "sold stake", "selling stake", "share sale"], "Stake Sale"),
        (["management buyout", "mbo", "leveraged buyout", "lbo"], "Buyout"),
        (["private equity"], "Private Equity"),
        (["business rescue"], "Business Rescue"),
        (["joint venture"], "Joint Venture"),
        (["bee transaction", "b-bbee"], "BEE Transaction"),
        (["cautionary", "firm intention", "firm offer"], "Cautionary/Offer"),
        (["takeover", "take-over", "taken over", "mandatory offer"], "Takeover"),
        (["recapitalisation", "recapitalization"], "Recapitalisation"),
    ]
    for keywords, deal_type in type_map:
        for kw in keywords:
            if kw in text_lower:
                return deal_type
    return "Other"


def calculate_relevance(text: str) -> tuple[int, list[str]]:
    text_lower = text.lower()
    matched = []
    score = 0

    for kw in DEAL_KEYWORDS:
        if kw.lower() in text_lower:
            matched.append(kw)
            score += 2

    # SA bonus only applies if at least one deal keyword matched
    if matched:
        sa_bonus = any(kw.lower() in text_lower for kw in SA_KEYWORDS)
        if sa_bonus:
            score += 5

    return score, matched


def scrape_rss_source(source_key: str) -> list[dict]:
    source = SOURCES[source_key]
    deals = []
    cutoff = datetime.utcnow() - timedelta(days=MAX_ARTICLE_AGE_DAYS)

    try:
        feed = feedparser.parse(source["url"], agent=HEADERS["User-Agent"])
        for entry in feed.entries:
            title = entry.get("title", "")
            summary = entry.get("summary", entry.get("description", ""))
            summary = BeautifulSoup(summary, "html.parser").get_text()[:500]
            link = entry.get("link", "")

            combined_text = f"{title} {summary}"
            relevance, matched_keywords = calculate_relevance(combined_text)

            if relevance < 2:
                continue

            published = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                published = datetime(*entry.published_parsed[:6])
            elif hasattr(entry, "published"):
                try:
                    published = date_parser.parse(entry.published)
                except (ValueError, TypeError):
                    pass

            if published and published.replace(tzinfo=None) < cutoff:
                continue

            deals.append({
                "title": title.strip(),
                "summary": summary.strip(),
                "url": link,
                "source": source["name"],
                "deal_type": classify_deal_type(combined_text),
                "companies": extract_companies(title),
                "published_date": published.isoformat() if published else "",
                "keywords_matched": ", ".join(matched_keywords),
                "relevance_score": relevance,
            })

    except Exception as e:
        logger.error(f"Error scraping {source['name']}: {e}")

    return deals


def scrape_sens() -> list[dict]:
    """Scrape JSE SENS announcements for M&A related news."""
    deals = []
    try:
        url = "https://www.jse.co.za/sens/sens-search"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            logger.warning(f"SENS returned status {resp.status_code}")
            return deals

        soup = BeautifulSoup(resp.text, "html.parser")
        articles = soup.select("article, .sens-item, .announcement, tr[data-url], .list-item")

        for article in articles[:50]:
            title_el = article.select_one("h2, h3, .title, td:first-child a, a")
            if not title_el:
                continue

            title = title_el.get_text(strip=True)
            link = title_el.get("href", "")
            if link and not link.startswith("http"):
                link = f"https://www.jse.co.za{link}"

            summary_el = article.select_one("p, .summary, td:nth-child(2)")
            summary = summary_el.get_text(strip=True)[:500] if summary_el else ""

            combined_text = f"{title} {summary}"
            relevance, matched_keywords = calculate_relevance(combined_text)

            if relevance < 2:
                continue

            deals.append({
                "title": title,
                "summary": summary,
                "url": link or url,
                "source": "JSE SENS",
                "deal_type": classify_deal_type(combined_text),
                "companies": extract_companies(title),
                "published_date": datetime.utcnow().isoformat(),
                "keywords_matched": ", ".join(matched_keywords),
                "relevance_score": relevance,
            })

    except Exception as e:
        logger.error(f"Error scraping SENS: {e}")

    return deals


def scrape_competition_commission() -> list[dict]:
    """Scrape SA Competition Commission for merger decisions."""
    deals = []
    try:
        url = "https://www.compcom.co.za/mergers-and-acquisitions/"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return deals

        soup = BeautifulSoup(resp.text, "html.parser")
        rows = soup.select("table tr, .merger-item, article, .entry")

        for row in rows[:30]:
            cells = row.select("td")
            if cells and len(cells) >= 2:
                title = cells[0].get_text(strip=True)
                summary = " | ".join(c.get_text(strip=True) for c in cells[1:])
            else:
                title_el = row.select_one("h2, h3, a, .title")
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                summary = row.get_text(strip=True)[:500]

            link_el = row.select_one("a[href]")
            link = link_el["href"] if link_el else url
            if link and not link.startswith("http"):
                link = f"https://www.compcom.co.za{link}"

            combined_text = f"{title} {summary}"
            relevance, matched_keywords = calculate_relevance(combined_text)

            if relevance < 2:
                relevance = 5
                matched_keywords = ["Competition Commission merger"]

            deals.append({
                "title": title[:200],
                "summary": summary[:500],
                "url": link,
                "source": "Competition Commission SA",
                "deal_type": classify_deal_type(combined_text),
                "companies": extract_companies(title),
                "published_date": "",
                "keywords_matched": ", ".join(matched_keywords),
                "relevance_score": relevance,
            })

    except Exception as e:
        logger.error(f"Error scraping Competition Commission: {e}")

    return deals


def scrape_dealmakers() -> list[dict]:
    """Scrape DealMakers SA for recent deal activity."""
    deals = []
    try:
        url = "https://www.dealmakerssouthafrica.com/"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return deals

        soup = BeautifulSoup(resp.text, "html.parser")
        articles = soup.select("article, .post, .deal-item, .entry, .news-item")

        for article in articles[:20]:
            title_el = article.select_one("h2 a, h3 a, .title a, a")
            if not title_el:
                continue

            title = title_el.get_text(strip=True)
            link = title_el.get("href", "")
            if link and not link.startswith("http"):
                link = f"https://www.dealmakerssouthafrica.com{link}"

            summary_el = article.select_one("p, .excerpt, .summary")
            summary = summary_el.get_text(strip=True)[:500] if summary_el else ""

            combined_text = f"{title} {summary}"
            relevance, matched_keywords = calculate_relevance(combined_text)
            if relevance < 1:
                relevance = 3
                matched_keywords = ["DealMakers listing"]

            deals.append({
                "title": title,
                "summary": summary,
                "url": link or url,
                "source": "DealMakers SA",
                "deal_type": classify_deal_type(combined_text),
                "companies": extract_companies(title),
                "published_date": "",
                "keywords_matched": ", ".join(matched_keywords),
                "relevance_score": relevance,
            })

    except Exception as e:
        logger.error(f"Error scraping DealMakers: {e}")

    return deals


def extract_companies(title: str) -> str:
    """Best-effort extraction of company names from title."""
    patterns = [
        r"(.+?)\s+(?:to\s+)?acquir(?:e|es|ed)\s+(.+?)(?:\s+for|\s+in|\.|$)",
        r"(.+?)\s+(?:and|&)\s+(.+?)\s+merg",
        r"(.+?)\s+(?:buys?|bought|purchases?)\s+(.+?)(?:\s+for|\s+in|\.|$)",
        r"(.+?)\s+(?:sells?|sold|disposes?\s+of)\s+(.+?)(?:\s+for|\s+to|\.|$)",
        r"(.+?)\s+(?:takes?\s+over|takeover\s+of)\s+(.+?)(?:\s+for|\s+in|\.|$)",
        r"(.+?)\s+(?:delist|delisting)",
    ]
    for pattern in patterns:
        match = re.search(pattern, title, re.IGNORECASE)
        if match:
            companies = [g.strip() for g in match.groups() if g]
            return ", ".join(companies[:2])
    return ""


def run_all_scrapers() -> list[dict]:
    """Run all scrapers and return combined results."""
    all_deals = []

    # RSS sources
    for key, source in SOURCES.items():
        if source["type"] == "rss":
            logger.info(f"Scraping RSS: {source['name']}")
            deals = scrape_rss_source(key)
            all_deals.extend(deals)
            logger.info(f"  Found {len(deals)} potential deals")

    # Web scrapers
    logger.info("Scraping JSE SENS...")
    all_deals.extend(scrape_sens())

    logger.info("Scraping Competition Commission...")
    all_deals.extend(scrape_competition_commission())

    logger.info("Scraping DealMakers SA...")
    all_deals.extend(scrape_dealmakers())

    logger.info(f"Total deals found this run: {len(all_deals)}")
    return all_deals
