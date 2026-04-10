"""Hassal Inc — Configuration"""

# Keywords that indicate M&A / liquidity events
DEAL_KEYWORDS = [
    "acquisition", "acquired", "acquire",
    "merger", "merge", "merged",
    "buyout", "buy-out", "bought",
    "takeover", "take-over", "taken over",
    "delisting", "delist", "delisted",
    "scheme of arrangement",
    "liquidity event",
    "private equity",
    "stake sale", "sold stake", "selling stake",
    "disposal", "disposed", "divest", "divestiture",
    "management buyout", "MBO",
    "leveraged buyout", "LBO",
    "controlling interest", "majority stake",
    "minority stake",
    "share purchase", "share sale",
    "business rescue",
    "unbundling", "unbundle",
    "joint venture",
    "recapitalisation", "recapitalization",
    "BEE transaction", "B-BBEE",
    "Competition Commission", "competition tribunal",
    "cautionary announcement",
    "firm intention", "firm offer",
    "mandatory offer",
    "Section 9", "Section 11",  # Companies Act sections relevant to M&A
]

# South Africa focus keywords (used to filter non-SA results)
SA_KEYWORDS = [
    "south africa", "south african",
    "johannesburg", "cape town", "durban", "pretoria",
    "JSE", "SENS",
    "rand", "ZAR",
    "Competition Commission",
    "CIPC",
    "BEE", "B-BBEE",
]

# RSS feeds and news sources
SOURCES = {
    "moneyweb": {
        "type": "rss",
        "url": "https://www.moneyweb.co.za/feed/",
        "name": "Moneyweb",
    },
    "biznews": {
        "type": "rss",
        "url": "https://www.biznews.com/feed",
        "name": "BizNews",
    },
    "news24_business": {
        "type": "rss",
        "url": "https://feeds.news24.com/articles/fin24/companies/rss",
        "name": "News24 Fin24",
    },
    "iol_business": {
        "type": "rss",
        "url": "https://www.iol.co.za/cmlink/business-report-rss-1.704533",
        "name": "IOL Business Report",
    },
    "businesslive": {
        "type": "rss",
        "url": "https://www.businesslive.co.za/bd/companies/rss",
        "name": "BusinessLIVE Companies",
    },
    "engineeringnews": {
        "type": "rss",
        "url": "https://www.engineeringnews.co.za/feed/",
        "name": "Engineering News",
    },
    "sens_jse": {
        "type": "web",
        "url": "https://www.jse.co.za/sens/sens-search",
        "name": "JSE SENS",
    },
    "dealmakers": {
        "type": "web",
        "url": "https://www.dealmakerssouthafrica.com/",
        "name": "DealMakers SA",
    },
    "competition_commission": {
        "type": "web",
        "url": "https://www.compcom.co.za/mergers-and-acquisitions/",
        "name": "Competition Commission SA",
    },
}

# Database
DB_PATH = "hassal_inc.db"

# How often to check (minutes)
CHECK_INTERVAL_MINUTES = 60

# Maximum age of articles to consider (days)
MAX_ARTICLE_AGE_DAYS = 30

# Console output width
CONSOLE_WIDTH = 120
