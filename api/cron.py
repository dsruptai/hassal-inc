"""Hassal Inc — Cron job: fetch deals, detect new ones, email alert"""

import os
import json
import hashlib
import urllib.request
from http.server import BaseHTTPRequestHandler
from datetime import datetime


ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()
RESEND_KEY = os.environ.get("RESEND_API_KEY", "").strip()
NOTIFY_EMAIL = "dalehas@gmail.com"
FROM_EMAIL = "Hassal Inc <onboarding@resend.dev>"  # Resend free tier sender

# Simple KV using Vercel KV or fallback to /tmp
SEEN_FILE = "/tmp/hassal_seen_deals.json"


def load_seen():
    try:
        with open(SEEN_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []


def save_seen(ids):
    try:
        with open(SEEN_FILE, "w") as f:
            json.dump(ids[-200:], f)  # Keep last 200
    except Exception:
        pass


def deal_id(ev):
    key = f"{ev.get('company','')}{ev.get('acquirer','')}{ev.get('type','')}".lower()
    return hashlib.md5(key.encode()).hexdigest()


def fetch_deals():
    today = datetime.utcnow().strftime("%Y-%m-%d")
    system = f"""SA M&A analyst. Use web search to find the latest South African deals from the last 7 days. Return ONLY raw JSON:
{{"events":[{{"company":"","type":"acquisition|merger|ipo|pe|buyout|bee|delisting|disposal","description":"1-2 sentences","dealValue":"","sector":"","acquirer":"","date":""}}]}}
Return 8-12 events. Only SA companies/assets. Today: {today}."""

    payload = {
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 3000,
        "system": system,
        "messages": [{"role": "user", "content": f"Search for South African M&A deals, Competition Commission merger approvals, JSE transactions from the last 7 days. Sources: BusinessTech, BusinessLIVE, News24, Moneyweb, BizNews, Fin24, compcom.co.za. Today is {today}. Return raw JSON only."}],
        "tools": [{"type": "web_search_20250305", "name": "web_search"}],
    }

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-api-key": ANTHROPIC_KEY,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    # Extract text block
    text_blocks = [b for b in data.get("content", []) if b.get("type") == "text"]
    if not text_blocks:
        return []

    raw = text_blocks[-1]["text"].strip()
    # Clean markdown fences
    raw = raw.replace("```json", "").replace("```", "").strip()

    # Find JSON
    s = raw.find("{")
    if s < 0:
        return []

    # Repair truncated JSON
    raw = raw[s:]
    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        # Try to repair
        import re
        raw = re.sub(r',\s*\{[^}]*$', '', raw)
        opens = raw.count('[') - raw.count(']')
        raw += ']' * max(0, opens)
        opens = raw.count('{') - raw.count('}')
        raw += '}' * max(0, opens)
        try:
            result = json.loads(raw)
        except json.JSONDecodeError:
            return []

    return result.get("events", [])


def send_email(new_deals):
    if not RESEND_KEY or not new_deals:
        return False

    deal_html = ""
    colors = {
        "acquisition": "#10b981", "merger": "#3b82f6", "ipo": "#14b8a6",
        "pe": "#f59e0b", "buyout": "#ec4899", "bee": "#a78bfa",
        "delisting": "#f43f5e", "disposal": "#f59e0b", "restructuring": "#3b82f6",
    }

    for ev in new_deals:
        t = (ev.get("type", "acquisition") or "acquisition").lower()
        color = colors.get(t, "#6366f1")
        deal_html += f"""
        <div style="background:#181b25;border:1px solid rgba(255,255,255,0.06);border-radius:8px;padding:14px 16px;margin-bottom:8px;border-left:3px solid {color};">
          <div style="margin-bottom:6px;">
            <span style="color:#f0f0f5;font-weight:700;font-size:14px;">{ev.get('company','Unknown')}</span>
            <span style="background:rgba(99,102,241,0.1);color:{color};font-size:10px;padding:2px 8px;border-radius:100px;margin-left:8px;font-weight:700;text-transform:uppercase;">{t}</span>
          </div>
          <p style="margin:0 0 8px;color:#8b8fa3;font-size:13px;line-height:1.5;">{ev.get('description','')}</p>
          <div style="font-size:12px;color:#4a4e63;">
            {f'<span style="color:#10b981;font-weight:600;">{ev.get("dealValue")}</span> · ' if ev.get('dealValue') else ''}
            {ev.get('sector','')} · {ev.get('date','')}
          </div>
        </div>"""

    html = f"""<html><body style="margin:0;padding:0;background:#08090d;font-family:'Helvetica Neue',Arial,sans-serif;">
    <div style="max-width:600px;margin:0 auto;padding:20px;">
    <div style="background:#12141c;border:1px solid rgba(255,255,255,0.06);border-radius:10px;overflow:hidden;">
      <div style="background:linear-gradient(135deg,#6366f1,#a78bfa);padding:20px 24px;">
        <h1 style="margin:0;color:white;font-size:20px;font-weight:700;">Hassal Inc</h1>
        <p style="margin:4px 0 0;color:rgba(255,255,255,0.8);font-size:13px;">New SA Deal Alert — {datetime.utcnow().strftime('%d %b %Y %H:%M UTC')}</p>
      </div>
      <div style="padding:16px 24px;border-bottom:1px solid rgba(255,255,255,0.06);">
        <span style="font-size:28px;font-weight:800;color:#818cf8;">{len(new_deals)}</span>
        <span style="font-size:13px;color:#8b8fa3;margin-left:8px;">new deal{'s' if len(new_deals) != 1 else ''} detected</span>
      </div>
      <div style="padding:20px 24px;">{deal_html}</div>
      <div style="padding:16px 24px;text-align:center;border-top:1px solid rgba(255,255,255,0.06);">
        <a href="https://hassal-inc.vercel.app" style="display:inline-block;background:#6366f1;color:white;padding:10px 28px;border-radius:8px;text-decoration:none;font-weight:600;font-size:13px;">View Dashboard</a>
      </div>
      <div style="padding:12px 24px;text-align:center;border-top:1px solid rgba(255,255,255,0.06);">
        <p style="margin:0;color:#4a4e63;font-size:10px;">Hassal Inc — Sources: Competition Commission · JSE SENS · DealMakers SA · BusinessTech · Moneyweb</p>
      </div>
    </div></div></body></html>"""

    email_payload = {
        "from": FROM_EMAIL,
        "to": [NOTIFY_EMAIL],
        "subject": f"Hassal Inc — {len(new_deals)} New SA Deal{'s' if len(new_deals) != 1 else ''} Detected",
        "html": html,
    }

    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=json.dumps(email_payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {RESEND_KEY}",
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.status == 200


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if not ANTHROPIC_KEY:
            self._respond(500, {"error": "ANTHROPIC_API_KEY not set"})
            return

        try:
            # Check if this is a test request
            is_test = "test" in self.path

            events = fetch_deals()
            seen = load_seen()
            seen_set = set(seen)

            new_deals = [ev for ev in events if deal_id(ev) not in seen_set]

            # Update seen list
            for ev in events:
                did = deal_id(ev)
                if did not in seen_set:
                    seen.append(did)
                    seen_set.add(did)
            save_seen(seen)

            email_sent = False
            if new_deals and RESEND_KEY:
                try:
                    email_sent = send_email(new_deals)
                except Exception as e:
                    email_sent = False

            self._respond(200, {
                "ok": True,
                "timestamp": datetime.utcnow().isoformat(),
                "total_found": len(events),
                "new_deals": len(new_deals),
                "email_sent": email_sent,
                "has_resend_key": bool(RESEND_KEY),
                "deals": [{"company": e.get("company"), "type": e.get("type")} for e in new_deals[:10]],
            })

        except Exception as e:
            self._respond(500, {"error": str(e)})

    def _respond(self, status, data):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))
