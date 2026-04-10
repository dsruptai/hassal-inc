"""Hassal Inc — Database layer (SQLite)"""

import sqlite3
import os
from datetime import datetime
from config import DB_PATH


def get_db_path():
    # On Vercel, only /tmp is writable
    if os.environ.get("VERCEL"):
        return os.path.join("/tmp", DB_PATH)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), DB_PATH)


def init_db():
    conn = sqlite3.connect(get_db_path())
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS deals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            summary TEXT,
            url TEXT UNIQUE,
            source TEXT,
            deal_type TEXT,
            companies TEXT,
            published_date TEXT,
            discovered_date TEXT NOT NULL,
            keywords_matched TEXT,
            relevance_score INTEGER DEFAULT 0
        )
    """)
    c.execute("""
        CREATE INDEX IF NOT EXISTS idx_deals_published ON deals(published_date DESC)
    """)
    c.execute("""
        CREATE INDEX IF NOT EXISTS idx_deals_source ON deals(source)
    """)
    c.execute("""
        CREATE INDEX IF NOT EXISTS idx_deals_relevance ON deals(relevance_score DESC)
    """)
    conn.commit()
    conn.close()


def deal_exists(url: str) -> bool:
    conn = sqlite3.connect(get_db_path())
    c = conn.cursor()
    c.execute("SELECT 1 FROM deals WHERE url = ?", (url,))
    exists = c.fetchone() is not None
    conn.close()
    return exists


def insert_deal(deal: dict) -> bool:
    if deal_exists(deal["url"]):
        return False
    conn = sqlite3.connect(get_db_path())
    c = conn.cursor()
    c.execute("""
        INSERT INTO deals (title, summary, url, source, deal_type, companies,
                          published_date, discovered_date, keywords_matched, relevance_score)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        deal["title"],
        deal.get("summary", ""),
        deal["url"],
        deal["source"],
        deal.get("deal_type", "Unknown"),
        deal.get("companies", ""),
        deal.get("published_date", ""),
        datetime.utcnow().isoformat(),
        deal.get("keywords_matched", ""),
        deal.get("relevance_score", 0),
    ))
    conn.commit()
    conn.close()
    return True


def get_deals(limit: int = 50, offset: int = 0, source: str = None,
              deal_type: str = None, search: str = None) -> list[dict]:
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    query = "SELECT * FROM deals WHERE 1=1"
    params = []

    if source:
        query += " AND source = ?"
        params.append(source)
    if deal_type:
        query += " AND deal_type = ?"
        params.append(deal_type)
    if search:
        query += " AND (title LIKE ? OR summary LIKE ? OR companies LIKE ?)"
        params.extend([f"%{search}%"] * 3)

    query += " ORDER BY discovered_date DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    c.execute(query, params)
    rows = [dict(row) for row in c.fetchall()]
    conn.close()
    return rows


def get_deal_count() -> int:
    conn = sqlite3.connect(get_db_path())
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM deals")
    count = c.fetchone()[0]
    conn.close()
    return count


def get_sources_summary() -> list[dict]:
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("""
        SELECT source, COUNT(*) as count,
               MAX(discovered_date) as last_checked
        FROM deals GROUP BY source ORDER BY count DESC
    """)
    rows = [dict(row) for row in c.fetchall()]
    conn.close()
    return rows


def get_deal_types_summary() -> list[dict]:
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("""
        SELECT deal_type, COUNT(*) as count
        FROM deals GROUP BY deal_type ORDER BY count DESC
    """)
    rows = [dict(row) for row in c.fetchall()]
    conn.close()
    return rows
