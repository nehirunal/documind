import os
from typing import List, Dict, Any
import requests
from datetime import datetime, timezone

from ..themes.selected import load_selected_senders
from ..themes.schemas import NewsletterItem
from ..utils.gmail_client import GmailClient  # sende zaten var gibi
from ..summarizer.summarizer import summarize_text  # kısa özet için (sende mevcut)

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

def _parse_from_header(h: str) -> Dict[str,str]:
    """
    'Ben's Bites <bensbites@example.com>' gibi From değerinden name/email ayrıştırır
    """
    name, email = "", ""
    if "<" in h and ">" in h:
        name = h.split("<",1)[0].strip().strip('"')
        email = h.split("<",1)[1].split(">",1)[0].strip().lower()
    else:
        # sadece e-posta olabilir
        email = h.strip().lower()
    return {"name": name or email, "email": email or h.strip().lower()}

def _iso_date(ms_or_iso: str | int) -> str:
    try:
        if isinstance(ms_or_iso, (int, float)) or (isinstance(ms_or_iso, str) and ms_or_iso.isdigit()):
            dt = datetime.fromtimestamp(int(ms_or_iso)/1000, tz=timezone.utc).astimezone()
            return dt.isoformat()
        if isinstance(ms_or_iso, str) and len(ms_or_iso) >= 10:
            return ms_or_iso
    except Exception:
        pass
    return datetime.now().astimezone().isoformat()

def collect_today_newsletters_and_ingest(user_id: str = "1") -> Dict[str, Any]:
    """
    1) seçili sender'ları yükle
    2) Gmail'den bugünün maillerini çek
    3) samurizer ile kısalt
    4) /themes/ingest'e POST et
    """
    selected = load_selected_senders()
    if not selected:
        return {"ok": False, "reason": "no_selected_senders"}

    g = GmailClient()  # senin mevcut client'ını kullanıyoruz (token vs hazır)

    # Bugünün başlangıcı (yerel saatle 00:00)
    today = datetime.now().astimezone()
    day_start = today.replace(hour=0, minute=0, second=0, microsecond=0)
    after_query = day_start.strftime("%Y/%m/%d")

    # Gmail query: after:YYYY/MM/DD ve senders filtresi
    # Gmail tarafında bir seferde tüm sender'lar yerine geniş çekip Python'da filtrelemek daha stabil.
    messages = g.search_messages(query=f'after:{after_query}')  # implementasyonu sende var

    items: List[NewsletterItem] = []
    for msg in messages:
        # msg = {"id": "...", "threadId": "...", "snippet": "...", "payload": {...}, "internalDate": "..."}
        headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
        frm = headers.get("from") or headers.get("sender") or ""
        if not frm:
            continue
        pe = _parse_from_header(frm)
        if pe["email"] not in selected:
            continue

        subject = headers.get("subject","").strip()
        # body (plain veya html temizlenmiş) — sende utils/text_clean olabilir
        body_text = g.get_message_body(msg)  # utils'in varsa onu kullan; yoksa snippet kullan
        if not body_text:
            body_text = msg.get("snippet","")

        # samurizer kısa özet
        short = summarize_text(body_text, max_sentences=2) if body_text else subject

        # Gmail web linki (kullanıcıya tıklanabilir)
        thread_id = msg.get("threadId") or ""
        web_url = f"https://mail.google.com/mail/u/0/#inbox/{thread_id}" if thread_id else None

        items.append(NewsletterItem(
            message_id = msg.get("id") or thread_id or subject or pe["email"],
            subject    = subject or pe["name"],
            body       = short or body_text or subject,
            date       = _iso_date(msg.get("internalDate","")),
            newsletter = pe["name"] or pe["email"],
            url        = web_url
        ))

    # Belleğe bas
    resp = requests.post(
        f"{BACKEND_URL}/themes/ingest",
        params={"user_id": user_id},
        json=[it.dict() for it in items],
        timeout=30
    )
    resp.raise_for_status()
    return {"ok": True, "ingested": len(items)}
