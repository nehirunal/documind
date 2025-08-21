from __future__ import annotations

import os
import re
import json
import sqlite3
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import requests

import aiohttp
import websockets
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from dotenv import load_dotenv

# ===================== ENV =====================
load_dotenv()

NEWSLY_API = "http://127.0.0.1:8000"
FORCE_ALL = True  # ana backend (featured burada)
MCP_WS = os.getenv("MCP_WS", "ws://localhost:8080")              # MCP gmail server
DEFAULT_TZ = os.getenv("DEFAULT_TZ", "Europe/Istanbul")
SENDER_FALLBACK = os.getenv("DIGEST_FROM", "Newsly.AI Digest")



# ===================== DB (abonelik) =====================
DB_PATH = os.getenv(
    "SUBSCRIBERS_DB",
    os.path.join(os.path.dirname(__file__), "..", "data", "newsly.db"),
)
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.execute(
    """
    CREATE TABLE IF NOT EXISTS subscribers (
        email TEXT PRIMARY KEY,
        tz TEXT NOT NULL DEFAULT 'Europe/Istanbul',
        created_at TEXT NOT NULL
    )
    """
)
conn.commit()

# ===================== MCP (gmail) =====================
async def mcp_call(ws, type_: str, payload: Optional[dict] = None):
    await ws.send(json.dumps({"type": type_, "payload": payload or {}}))
    while True:
        raw = await ws.recv()
        msg = json.loads(raw)
        mtype = msg.get("type", "")
        if mtype == "connected":
            continue
        if mtype == f"{type_}.result" and "result" in msg:
            return msg
        if mtype == f"{type_}.error" or "error" in msg:
            err = msg.get("error") or msg.get("result", {}).get("error") or "unknown_error"
            raise RuntimeError(f"MCP error ({type_}): {err}")

async def gmail_send(to: str, subject: str, body_html: str, body_text: Optional[str] = None):
    """
    MCP gmail.send → {to, subject, html, text}
    HTML multipart/alternative olarak gider.
    """
    async with websockets.connect(MCP_WS) as ws:
        await ws.send(json.dumps({"type": "connect", "agent_name": "DailyDigestAgent", "version": "1.0"}))
        payload = {"to": to, "subject": subject, "html": body_html}
        if body_text is not None:
            payload["text"] = body_text
        r = await mcp_call(ws, "gmail.send", payload)
        if r.get("result", {}).get("status") != "ok":
            raise RuntimeError(f"gmail.send failed: {r}")

# ===================== Backend helpers =====================
def _parse_iso(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        s2 = s.strip()
        if s2.endswith("Z"):
            s2 = s2[:-1] + "+00:00"
        return datetime.fromisoformat(s2)
    except Exception:
        return None
    
def fetch_featured_from_backend_sync(fast: int = 0, timeout_s: int = 120):
    url = f"{NEWSLY_API}/api/newsletters/featured?fast={fast}"
    print("[AGENT] GET", url)
    try:
        r = requests.get(url, timeout=timeout_s)
        print("[AGENT] status", r.status_code)
        r.raise_for_status()
        j = r.json()
        items = j.get("items", []) or []
        print(f"[AGENT] items={len(items)} (fast={fast})")
        return [it for it in items if isinstance(it, dict)]
    except Exception as e:
        print("[AGENT] fetch error:", type(e).__name__, e)
        return []
    
    



async def fetch_featured_from_backend(fast: int = 0, timeout_s: int = 120) -> List[Dict[str, Any]]:
    url = f"{NEWSLY_API}/api/newsletters/featured?fast={fast}"
    print("[AGENT] GET", url)
    try:
        import aiohttp
        timeout = aiohttp.ClientTimeout(total=timeout_s, connect=5)
        async with aiohttp.ClientSession(timeout=timeout) as sess:
            async with sess.get(url) as resp:
                data = await resp.json()
                items = data.get("items", []) or []
                print(f"[AGENT] featured fast={fast} -> {len(items)} items, status={resp.status}")
                return [it for it in items if isinstance(it, dict)]
    except Exception as e:
        print("[featured fetch error]", type(e).__name__, e)
        return []


# ===================== HTML / TEXT =====================
ZW_RE = re.compile(r"[\u200B-\u200F\u202A-\u202E\u2060-\u206F\uFEFF\u034F]")  # zero-width & bidi, CGJ
NBSP_RE = re.compile(r"(?:\u00A0|&nbsp;)")
MULTISPACE_RE = re.compile(r"[ \t]{2,}")
SENT_SPLIT = re.compile(r"(?<=[\.!?])\s+(?=[A-ZİIĞÜŞÖ0-9])", re.U)

WARNING_PREFIX = "Bugün gelen seçili bülten bulunamadı"  # kart içi maddelere asla girmesin

def sanitize_text(s: str | None) -> str:
    if not s:
        return ""
    s = ZW_RE.sub("", s)
    s = NBSP_RE.sub(" ", s)
    s = s.replace("\r", " ").replace("\n", " ")
    s = MULTISPACE_RE.sub(" ", s)
    return s.strip()

def escape_html(s: str | None) -> str:
    s = sanitize_text(s)
    # temel kaçış
    return (
        s.replace("&", "&amp;")
         .replace("<", "&lt;")
         .replace(">", "&gt;")
    )

def html_to_text(html: str) -> str:
    html = sanitize_text(html)
    txt = re.sub(r"<br\s*/?>", "\n", html)
    txt = re.sub(r"<li[^>]*>", "• ", txt)
    txt = re.sub(r"</li>", "\n", txt)
    txt = re.sub(r"<[^>]+>", "", txt)
    txt = NBSP_RE.sub(" ", txt)
    txt = re.sub(r"\n{3,}", "\n\n", txt)
    return txt.strip()

def derive_highlights(
    highlights: Optional[List[str]],
    teaser: str,
    long_summary: str,
    max_items: int = 4
) -> List[str]:
    """
    Highlights boşsa veya 'Sender:' gibi işe yaramazsa,
    teaser/long_summary içinden anlamlı 3–4 cümle üret.
    """
    def clean_list(lst: List[str]) -> List[str]:
        out = []
        for x in lst:
            if not x:
                continue
            t = sanitize_text(x)
            if not t or t.lower().startswith("sender:"):
                continue
            if WARNING_PREFIX.lower() in t.lower():
                continue
            out.append(t)
        return out

    # 1) Var olan highlight'ları temizleyip kullan
    if highlights:
        hl = clean_list(highlights)
        if hl:
            return hl[:max_items]

    # 2) Teaser cümlelerine bak (uyarı değilse)
    hl = []
    if teaser and WARNING_PREFIX.lower() not in teaser.lower():
        parts = [p.strip() for p in SENT_SPLIT.split(teaser) if p.strip()]
        hl = clean_list(parts)
        if hl:
            return hl[:max_items]

    # 3) Long summary cümlelerinden seç
    if long_summary:
        parts = [p.strip() for p in SENT_SPLIT.split(long_summary) if p.strip()]
        hl = clean_list(parts)
        if hl:
            return hl[:max_items]

    return []


def _esc(s: str) -> str:
    s = (s or "")
    return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

def _br(s: str) -> str:
    # newline → <br> (HTML email uyumu)
    return _esc(s).replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br>")

def get_long_summary(it: dict) -> str:
    """
    UI’da gelebilecek tüm olası alanları birleştirir:
    - long_summary
    - long
    - full_summary / summary (listeyse birleştir)
    - yoksa "" döner
    """
    long_text = (it.get("long_summary")
                 or it.get("long")
                 or "")
    if not long_text:
        fs = it.get("full_summary") or it.get("summary")
        if isinstance(fs, list):
            long_text = " ".join(str(x).strip() for x in fs if str(x).strip())
    return (long_text or "").strip()


def build_html_from_featured(date_local, items: list[dict], global_notice: str | None = None) -> str:
    date_str = date_local.strftime("%d %B %Y")

    head = f"<h2 style='margin:0 0 12px'>Newsly.AI – Günlük Özet · {_esc(date_str)}</h2>"
    sub  = "<p style='color:#475569;margin:0 0 20px'>Bugün ana sayfadaki seçili bültenlerin özetleri.</p>"
    notice_html = (
        f"<div style='margin:8px 0 16px;font-size:12px;color:#64748b'>{_esc(global_notice or '')}</div>"
        if global_notice else ""
    )

    cards_html = []
    for it in items:
        title        = _esc(it.get("title") or "(Başlıksız)")
        sender       = _esc(it.get("sender") or "")
        highlights   = it.get("highlights") or []
        teaser       = (it.get("teaser") or it.get("description") or "").strip()
        long_summary = get_long_summary(it)

        inner_parts = []

        # 1) Key Insights (max 4) — UI ile aynı davranış
        if isinstance(highlights, list) and len(highlights) > 0:
            lis = "".join(
                f"<li style='margin:4px 0'>{_esc(str(h))}</li>"
                for h in highlights[:4] if str(h).strip()
            )
            inner_parts.append(
                "<div style='display:flex;align-items:center;gap:8px;margin:8px 0 6px'>"
                "<span style='font-size:12px;color:#ea580c;font-weight:700;letter-spacing:.02em;text-transform:uppercase'>Key Insights</span>"
                "</div>"
                f"<ul style='padding-left:18px;margin:0 0 10px'>{lis}</ul>"
            )

        # 2) Newsletter Summary — HER ZAMAN bas (UI “summary” bölümü)
        summary_text = (
            long_summary if long_summary
            else (teaser if teaser and not teaser.lower().startswith("sender:") else "")
        )
        if not summary_text:
            summary_text = "(özet bulunamadı)"

        inner_parts.append(
            "<div style='display:flex;align-items:center;gap:8px;margin:6px 0 6px'>"
            "<div style='width:20px;height:20px;border-radius:6px;background:#334155;display:flex;align-items:center;justify-content:center'>"
            "<span style='font-size:11px;color:#fff;font-weight:700'>S</span></div>"
            "<span style='font-size:12px;color:#334155;font-weight:700;letter-spacing:.02em;text-transform:uppercase'>Newsletter Summary</span>"
            "</div>"
            f"<div style='font-size:14px;color:#334155;line-height:1.6'>{_br(summary_text)}</div>"
        )

        cards_html.append(
            "<div style='border:1px solid #e2e8f0;border-radius:12px;padding:14px 16px;margin:12px 0'>"
            f"<div style='font-size:13px;color:#0ea5e9;margin-bottom:6px'>{sender}</div>"
            f"<div style='font-weight:700;color:#0f172a;margin-bottom:8px'>{title}</div>"
            f"{''.join(inner_parts)}"
            "</div>"
        )

    footer = (
        f"<p style='color:#64748b;font-size:12px;margin-top:16px'>"
        f"Bu e-postayı saat {_esc(date_local.strftime('%H:%M'))}'de otomatik olarak aldınız. "
        f"Abonelikten çıkmak için yanıtlayın."
        f"</p>"
    )

    return (
        "<div style='font-family:ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,"
        "Cantarell,Noto Sans,sans-serif;background:#f8fafc;padding:24px'>"
          "<div style='max-width:680px;margin:0 auto;background:#ffffff;border:1px solid #e2e8f0;"
          "border-radius:16px;padding:20px 24px'>"
            f"{head}{sub}{notice_html}{''.join(cards_html)}{footer}"
          "</div>"
        "</div>"
    )


# ===================== Digest akışı =====================
async def send_daily_digest(to_email: str) -> str:
    tz = ZoneInfo(DEFAULT_TZ)
    now_local = datetime.now(tz)

    # UI ile aynı kaynak
    items = fetch_featured_from_backend_sync(fast=0, timeout_s=420)
    if not items:
        items = fetch_featured_from_backend_sync(fast=1, timeout_s=120)
    if not items:
        return "Bugün için listelenecek özet yok."

    # Bugün filtresi istiyorsan kalsın; yoksa direkt en güncel ilk 5:
    items_sorted = sorted(
        [it for it in items if _parse_iso(it.get("date"))],
        key=lambda x: (_parse_iso(x.get("date")) or datetime.min.replace(tzinfo=timezone.utc)),
        reverse=True,
    )
    items_use = items_sorted[:5]

    html = build_html_from_featured(now_local, items_use, global_notice=None)
    text = html_to_text(html)
    subject = f"Newsly.AI · Günlük Özet ({now_local.strftime('%d.%m.%Y')})"
    await gmail_send(to_email, subject, html, body_text=text)
    return f"{to_email} için günlük özet gönderildi."


# ===================== FastAPI =====================
app = FastAPI(title="Newsly Daily Digest Agent")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SubscribeBody(BaseModel):
    email: EmailStr
    tz: Optional[str] = None  # default Europe/Istanbul

@app.post("/api/subscriptions")
def subscribe(body: SubscribeBody):
    tz = body.tz or DEFAULT_TZ
    try:
        ZoneInfo(tz)
    except Exception:
        raise HTTPException(400, detail="Geçersiz timezone")

    with conn:
        conn.execute(
            "INSERT OR REPLACE INTO subscribers (email, tz, created_at) VALUES (?, ?, ?)",
            (body.email, tz, datetime.utcnow().isoformat()),
        )
    return {"ok": True}

@app.get("/api/subscriptions")
def list_subs():
    cur = conn.execute("SELECT email, tz, created_at FROM subscribers ORDER BY created_at DESC")
    return {"items": [{"email": e, "tz": tz, "created_at": ca} for (e, tz, ca) in cur.fetchall()]}

class NowBody(BaseModel):
    email: EmailStr

@app.get("/api/digest/preview")
async def digest_preview():
    tz = ZoneInfo(DEFAULT_TZ)
    now_local = datetime.now(tz)
    # UI ile AYNI: fast=0, uzun timeout
    items = fetch_featured_from_backend_sync(fast=0, timeout_s=420)
    if not items:
        # son çare: fast=1
        items = fetch_featured_from_backend_sync(fast=1, timeout_s=120)
    if not items:
        return {"html": "<p>Öğe yok</p>"}
    html = build_html_from_featured(now_local, items[:5], global_notice=None)
    return {"html": html}


@app.post("/api/digest/now")
async def trigger_now(body: NowBody):
    tz = ZoneInfo(DEFAULT_TZ)
    now_local = datetime.now(tz)
    items = fetch_featured_from_backend_sync(fast=0, timeout_s=420)
    if not items:
        items = fetch_featured_from_backend_sync(fast=1, timeout_s=120)
    if not items:
        return {"ok": False, "message": "featured boş geldi (fast=0/1)"}
    items_use = items[:5]
    # items_use oluşturduktan hemen sonra:
    for idx, it in enumerate(items_use):
        long_text = (it.get("long_summary") or it.get("long") or "")
        if not long_text:
            fs = it.get("full_summary") or it.get("summary")
            if isinstance(fs, list):
               long_text = " ".join(str(x).strip() for x in fs if str(x).strip())
        teaser = (it.get("teaser") or it.get("description") or "").strip()
        print(
             f"[AGENT] card#{idx} sender={it.get('sender')} "
             f"title={str(it.get('title'))[:40]!r} "
             f"hl={len(it.get('highlights') or [])} "
             f"long_len={len(long_text)} teaser_len={len(teaser)}"
        )

    html = build_html_from_featured(now_local, items_use, global_notice=None)
    text = html_to_text(html)
    subject = f"Newsly.AI · Günlük Özet ({now_local.strftime('%d.%m.%Y')})"
    await gmail_send(body.email, subject, html, body_text=text)
    return {"ok": True, "message": f"{body.email} için gönderildi."}



# ===================== Scheduler (18:00) =====================
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

scheduler: Optional[AsyncIOScheduler] = None

async def job_run_for_tz(tz_name: str):
    cur = conn.execute("SELECT email FROM subscribers WHERE tz = ?", (tz_name,))
    emails = [r[0] for r in cur.fetchall()]
    for email in emails:
        try:
            print(f"[Digest] {tz_name} -> {email}")
            await send_daily_digest(email)
        except Exception as e:
            print("[Digest ERROR]", email, e)

@app.on_event("startup")
async def on_start():
    global scheduler
    scheduler = AsyncIOScheduler()
    cur = conn.execute("SELECT DISTINCT tz FROM subscribers")
    tz_list = [r[0] for r in cur.fetchall()] or [DEFAULT_TZ]

    for tz in tz_list:
        trig = CronTrigger(hour=18, minute=0, timezone=ZoneInfo(tz))
        scheduler.add_job(job_run_for_tz, trigger=trig, args=[tz], id=f"digest-{tz}", replace_existing=True)
        print("[Scheduler] Job eklendi:", tz)

    scheduler.start()

@app.on_event("shutdown")
async def on_stop():
    if scheduler:
        scheduler.shutdown()

# ===================== Basit test =====================
@app.post("/api/test/send_html")
async def test_send_html(body: NowBody):
    html = "<h1 style='margin:0'>HTML Test</h1><p>Bu bir <b>HTML</b> gövdesidir.</p>"
    text = "HTML Test\nBu bir HTML gövdesidir."
    await gmail_send(body.email, "Newsly HTML Test", html, body_text=text)
    return {"ok": True}

# ===================== Local run =====================
if __name__ == "__main__":
    import uvicorn
    # İlk kullanımda OAuth, backend/mcp/server.py çalışıyorken alınır (tarayıcı açılır).
    uvicorn.run(app, host="0.0.0.0", port=8001)
