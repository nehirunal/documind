# backend/utils/gmail_scan.py
from __future__ import annotations

import base64
import datetime as dt
from typing import Any, Dict, List, Optional, Tuple

from googleapiclient.discovery import Resource

# Yetkili Gmail servisi
from backend.utils.gmail_client import get_gmail_service


# ---------- servis ----------
def _gmail() -> Resource:
    """Authorized Gmail service client döndürür."""
    return get_gmail_service()


# ---------- yardımcılar (MIME/gövde/başlık) ----------
def _flatten_parts(parts: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for p in parts or []:
        if "parts" in p:
            out.extend(_flatten_parts(p.get("parts")))
        else:
            out.append(p)
    return out


def _decode_b64url(data: str) -> str:
    if not data:
        return ""
    pad = len(data) % 4
    if pad:
        data += "=" * (4 - pad)
    try:
        return base64.urlsafe_b64decode(data.encode()).decode("utf-8", errors="ignore")
    except Exception:
        return ""


def _extract_headers(payload: Dict[str, Any]) -> Dict[str, str]:
    headers = payload.get("headers", []) if payload else []
    return {h.get("name", ""): h.get("value", "") for h in headers if isinstance(h, dict)}


def _extract_best_body(payload: Dict[str, Any]) -> str:
    """
    Mesajdan öncelikle text/plain, yoksa text/html, yoksa payload.body.data,
    son çare snippet döndür (snippet bu fonksiyonun dışında ele alınır).
    """
    if not payload:
        return ""

    # 1) parts içinden plain/html ara
    parts = payload.get("parts")
    if parts:
        flat = _flatten_parts(parts)
        text_part = next(
            (p for p in flat if p.get("mimeType") == "text/plain" and p.get("body", {}).get("data")),
            None,
        )
        html_part = next(
            (p for p in flat if p.get("mimeType") == "text/html" and p.get("body", {}).get("data")),
            None,
        )
        if text_part:
            return _decode_b64url(text_part["body"]["data"])
        if html_part:
            return _decode_b64url(html_part["body"]["data"])

    # 2) bazı maillerde gövde direkt payload.body.data'da olur
    body_data = payload.get("body", {}).get("data")
    if body_data:
        return _decode_b64url(body_data)

    # 3) burada snippet'e düşmüyoruz; dışarıda ele alınacak
    return ""


def _list_messages(service: Resource, q: str, max_results: int = 50) -> List[Dict[str, Any]]:
    resp = service.users().messages().list(userId="me", q=q, maxResults=max_results).execute()
    return resp.get("messages", []) or []


# ---------- yardımcılar (adres/isim/tarih) ----------
def _parse_email_address(from_header: str) -> str:
    """
    'Name <addr@example.com>' -> 'addr@example.com'
    """
    if not from_header:
        return ""
    s = from_header.strip()
    if "<" in s and ">" in s:
        s = s.split("<", 1)[1].split(">", 1)[0]
    return s.strip().strip('"').lower()


def _guess_display_name(from_header: str) -> str:
    """
    'Name <addr@example.com>' -> 'Name'
    """
    if not from_header:
        return ""
    s = from_header.strip()
    if "<" in s:
        s = s.split("<", 1)[0]
    return s.strip().strip('"')


def _to_iso(date_header: str) -> str:
    """
    RFC822 tarihten ISO 8601'ye dönüşüm. Hata olursa epoch'a düşer.
    """
    if not date_header:
        return "1970-01-01T00:00:00Z"
    try:
        from email.utils import parsedate_to_datetime
        dt_obj = parsedate_to_datetime(date_header)  # timezone-aware
        return dt_obj.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    except Exception:
        return "1970-01-01T00:00:00Z"


# ---------- aday tarama ----------
def scan_candidates(user_email: Optional[str] = None, lookback_days: int = 30) -> List[Dict[str, Any]]:
    """
    Gelen kutusundan son X gün içindeki iletilerden potansiyel bülten göndericilerini çıkarır.
    DÖNÜŞ: [{ "name": "...", "sender": "newsletter@example.com" }, ...]
    """
    service = _gmail()

    # Kategorileri gruplayalım; Gmail query parantezlerini ekle
    query = f'newer_than:{lookback_days}d (category:updates OR label:^smartlabel_newsletter)'
    msgs = _list_messages(service, q=query, max_results=200)

    senders: Dict[str, str] = {}
    for m in msgs:
        msg = service.users().messages().get(
            userId="me",
            id=m["id"],
            format="metadata",
            metadataHeaders=["From", "Subject"],
        ).execute()
        headers = _extract_headers(msg.get("payload", {}))
        from_raw = headers.get("From", "")
        sender_email = _parse_email_address(from_raw)
        if not sender_email:
            continue
        name = _guess_display_name(from_raw) or sender_email.split("@")[0]
        senders.setdefault(sender_email, name)

    # Liste formatına çevir
    candidates = [{"name": name, "sender": sender} for sender, name in senders.items()]
    candidates.sort(key=lambda x: (x["name"] or "").lower())
    return candidates


# ---------- içerik çekme ----------
def fetch_latest_email_content_for_sender(
    user_email: Optional[str],
    sender_email: str,
    lookback_days: int = 120,  # daha geniş pencere
) -> Tuple[str, str]:
    """
    Belirli bir göndericiden gelen en son e-postanın metnini ve tarihini döndürür.
    DÖNÜŞ: (content, iso_date)
    """
    if not sender_email:
        return "", "1970-01-01T00:00:00Z"

    service = _gmail()

    q = f'from:{sender_email} newer_than:{lookback_days}d'
    msgs = _list_messages(service, q=q, max_results=1)
    if not msgs:
        return "", "1970-01-01T00:00:00Z"

    msg_id = msgs[0]["id"]
    msg = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
    payload = msg.get("payload", {})

    content = _extract_best_body(payload)
    if not content:
        # en son çare: snippet
        content = (msg.get("snippet") or "").strip()

    headers = _extract_headers(payload)
    date_str = headers.get("Date", "")
    iso_date = _to_iso(date_str)

    return content, iso_date
