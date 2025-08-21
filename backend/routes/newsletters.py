# backend/routes/newsletters.py
from __future__ import annotations

import os
import json
import logging
import traceback
import re
import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime
from zoneinfo import ZoneInfo

IST = ZoneInfo("Europe/Istanbul")

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from backend.nlp.topic_labeler import label_newsletter
from backend.config.paths import SAVE_PATH, DATA_DIR
from backend.utils.gmail_scan import (
    scan_candidates,
    fetch_latest_email_content_for_sender,
)
from backend.utils.text_clean import clean_text
from backend.summarizer.summarizer import summarize_newsletter_tiered

router = APIRouter(prefix="/api/newsletters", tags=["newsletters"])
logger = logging.getLogger(__name__)

# ----------------- Yardımcılar -----------------

SENT_SPLIT = re.compile(r"(?<=[\.!?])\s+(?=[A-ZİIĞÜŞÖ0-9])", re.U)

# İngilizce + Türkçe anahtarlar: ürün, kampanya, politika, araştırma vb.
_KEYWORDS = [
    # EN
    "sale", "discount", "deal", "offer", "launch", "update", "policy",
    "research", "report", "funding", "merger", "acquisition", "feature",
    "security", "privacy", "climate", "economy", "market", "earnings",
    # TR
    "kampanya", "indirim", "fırsat", "duyuru", "güncelleme", "tasarı",
    "yasa", "karar", "araştırma", "rapor", "yatırım", "fonlama",
    "birleşme", "satın alma", "özellik", "güvenlik", "mahremiyet",
    "iklim", "ekonomi", "piyasa", "kazanç",
]


def _ensure_data_dir() -> None:
    """DATA_DIR ve SAVE_PATH'in klasörünü garantiye al."""
    os.makedirs(DATA_DIR, exist_ok=True)
    sp_dir = os.path.dirname(SAVE_PATH)
    if sp_dir:
        os.makedirs(sp_dir, exist_ok=True)


def _score_sentence(sent: str) -> float:
    """Anahtar kelime + uzunluk puanı."""
    s = sent.lower()
    kw = sum(1 for k in _KEYWORDS if k in s)
    length_bonus = min(len(sent) / 120, 1.0)  # 120+ karaktere kadar bonus
    return kw * 2.0 + length_bonus


def pick_sentences(txt: str, max_count: int, min_len: int = 40) -> List[str]:
    """Temiz metinden anlamlı cümle seçer; unsub/cta içerikleri eler."""
    parts = [p.strip() for p in SENT_SPLIT.split(txt) if p and len(p.strip()) >= min_len]
    cleaned = []
    for p in parts:
        low = p.lower()
        if any(u in low for u in [
            "unsubscribe", "view email in browser", "view in browser",
            "manage preferences", "privacy policy", "contact us",
            "in partnership with", "sponsored", "advertiser content",
            "read in browser", "read on the web", "open in browser",
        ]):
            continue
        cleaned.append(p)
    cleaned.sort(key=_score_sentence, reverse=True)
    out: List[str] = []
    seen: set = set()
    for c in cleaned:
        key = c[:80]
        if key in seen:
            continue
        out.append(c)
        seen.add(key)
        if len(out) >= max_count:
            break
    return out


def build_fallbacks(clean_content: str):
    """Highlights(3–4), Teaser(=highlights birleşimi), Long(15–20) üretir."""
    highlights = pick_sentences(clean_content, 4, min_len=50)
    long_sents = pick_sentences(clean_content, 20, min_len=40)
    teaser = " ".join(highlights) if highlights else (
        clean_content[:300] + "…" if len(clean_content) > 300 else clean_content
    )
    long_summary = " ".join(long_sents) if long_sents else teaser
    if long_summary.strip() == teaser.strip() and len(clean_content) > 1500:
        long_summary = clean_content[:1500] + "…"
    return teaser.strip(), long_summary.strip(), highlights


def _safe_topic(name: str) -> str:
    n = (name or "").lower()
    if any(k in n for k in ["ai", "ml", "tech", "brew"]):
        return "Technology"
    if any(k in n for k in ["biz", "market", "finance", "bloomberg", "wall"]):
        return "Business"
    if any(k in n for k in ["design", "ux", "ui"]):
        return "Design"
    return "General"

# ----------------- Endpoints -----------------


@router.post("/scan")
def scan_newsletters():
    """
    Gmail'inde son 30 günde görünen bülten gönderenlerini tarar.
    Hepsini varsayılan olarak 'selected': true işaretler (UI üzerinden kaydedebilirsin).
    """
    try:
        _ensure_data_dir()
        user_email: Optional[str] = None
        candidates: List[Dict[str, Any]] = scan_candidates(user_email)
        for c in candidates:
            c["selected"] = True
        return {"candidates": candidates}
    except Exception as e:
        logger.exception("scan_newsletters failed")
        return JSONResponse(
            status_code=500,
            content={"error": f"{type(e).__name__}: {e}", "trace": traceback.format_exc()},
        )


@router.post("/selection")
def save_selection(payload: Dict[str, Any]):
    """
    Beklenen gövde:
    {
      "selected": [
        {"name": "...", "sender": "...", "count30d": 0, "selected": true},
        ...
      ]
    }
    """
    try:
        _ensure_data_dir()
        items = payload.get("selected", [])
        if not isinstance(items, list):
            raise HTTPException(status_code=422, detail="`selected` listesi bekleniyor")

        cleaned: List[Dict[str, Any]] = []
        for it in items:
            sender = (it or {}).get("sender", "").strip()
            name = (it or {}).get("name", "").strip() or sender
            if not sender:
                continue
            cleaned.append({
                "name": name,
                "sender": sender,
                "count30d": int((it or {}).get("count30d", 0) or 0),
                "selected": bool((it or {}).get("selected", True)),
            })

        data = {"version": 1, "selected": cleaned}
        with open(SAVE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return {"ok": True, "saved": len(cleaned), "path": SAVE_PATH}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("save_selection failed")
        return JSONResponse(
            status_code=500,
            content={"error": f"{type(e).__name__}: {e}", "trace": traceback.format_exc()},
        )


@router.get("/featured")
async def get_featured(fast: int = 0):
    """
    Ana sayfada gösterilecek kartları üretir.
    - fast=1 → Hızlı mod (ama yine de son e-postadan kısa özet üretir).
    - fast=0 → Her seçili gönderici için son e-postayı getirip (timeout'lu) özet üretir.
    """
    items: List[Dict[str, Any]] = []
    try:
        _ensure_data_dir()
        if not os.path.exists(SAVE_PATH):
            return {"items": []}

        with open(SAVE_PATH, "r", encoding="utf-8") as f:
            data = json.loads(f.read() or "{}")

        selected = data.get("selected", [])
        if not isinstance(selected, list) or not selected:
            return {"items": []}

        # Ayarları biraz konservatif yapalım
        MAX_CARDS = 12
        LOOKBACK_DAYS = 120
        PER_SENDER_TIMEOUT = 25.0  # saniye
        MAX_CARDS_FAST = 5


        for i, it in enumerate(selected[: (MAX_CARDS_FAST if fast else MAX_CARDS)]):

            name = (it.get("name") or it.get("sender") or "Unknown").strip()
            sender = (it.get("sender") or "").strip()
            if not sender:
                continue

            # Ortak alanlar
            iso_date = "1970-01-01T00:00:00Z"
            title = name
            teaser = ""
            long_summary = ""
            highlights: List[str] = []
            clean_content: str = ""  # tag üretiminde de kullanacağız

            # is_today (sonradan iso_date güncellenebilir)
            is_today = False

            if fast:
            # FAST MODE: içerik çek + FALLOBACK özet (çok hızlı)
                try:
                    content, iso_date = fetch_latest_email_content_for_sender(
                        None, sender, LOOKBACK_DAYS
                    )
                    clean_content = clean_text(content or "")
                except Exception:
                  clean_content = ""

                if clean_content:
                   teaser, long_summary, highlights = build_fallbacks(clean_content)
                   title = title or name
                else:
                  teaser = f"Sender: {sender}"
                  long_summary = teaser
                  highlights = []

            else:
                # NORMAL MODE: Gmail’den içerik çekmeye çalış (timeout'lu ve thread offload)
                content: str = ""
                try:
                    logger.info("Fetching latest email for sender=%s", sender)
                    content, iso_date = await asyncio.wait_for(
                        asyncio.to_thread(
                            fetch_latest_email_content_for_sender,
                            None,            # user_email (None → 'me')
                            sender,          # sender_email
                            LOOKBACK_DAYS,
                        ),
                        timeout=PER_SENDER_TIMEOUT,
                    )
                    logger.info("Fetched OK for %s, len=%d", sender, len(content or ""))
                except asyncio.TimeoutError:
                    logger.warning("Gmail fetch TIMEOUT for %s", sender)
                except Exception as e:
                    logger.warning("Gmail fetch ERROR for %s: %s", sender, e)

                # temizle
                try:
                    clean_content = clean_text(content or "")
                except Exception:
                    clean_content = content or ""

                if not clean_content or len(clean_content) < 40:
                    clean_content = (content or "").strip()

                # özetle (tiered)
                if clean_content:
                    try:
                        tiered = summarize_newsletter_tiered(
                            clean_content, sender=name, date_iso=iso_date or ""
                        )
                        title = (tiered.get("title") or name).strip()
                        teaser = (tiered.get("teaser") or "").strip()
                        long_summary = (tiered.get("long") or "").strip()
                        highlights = (tiered.get("highlights") or [])[:4]
                    except Exception as e:
                        logger.warning("summarize_newsletter_tiered failed for %s: %s", sender, e)

                # Fallback garanti
                if not teaser and not long_summary:
                    base = clean_content or "No preview available."
                    teaser = (base[:300] + "…") if len(base) > 300 else base
                    long_summary = teaser

            # Highlights hâlâ boşsa, teaser/long_summary’dan üret
            if not highlights:
                tparts = [p.strip() for p in SENT_SPLIT.split(teaser or "") if p.strip()]
                lparts = [p.strip() for p in SENT_SPLIT.split(long_summary or "") if p.strip()]
                highlights = (tparts or lparts)[:4]

            # is_today’ı iso_date’e göre hesapla
            try:
                if iso_date and iso_date != "1970-01-01T00:00:00Z":
                    dt = datetime.fromisoformat(iso_date.replace("Z", "+00:00")).astimezone(IST)
                    is_today = dt.date() == datetime.now(IST).date()
            except Exception:
                is_today = False

            topic = _safe_topic(f"{name} {sender}")
            words = len((teaser + " " + long_summary).split())
            minutes = max(1, words // 180)

            try:
                tag = label_newsletter(title or "", (clean_content or teaser or long_summary or ""))
            except Exception:
                tag = "General"

            items.append({
                "id": i,
                "title": title,
                "topic": topic,
                "minutes": minutes,
                "tag": tag,
                "description": teaser,
                "teaser": teaser,
                "long_summary": long_summary,
                "highlights": highlights,
                "sender": sender,
                "date": iso_date or "1970-01-01T00:00:00Z",
                "is_today": is_today,
            })

        # en yeni üstte
        items.sort(key=lambda x: x["date"], reverse=True)
        return {"items": items}
    except Exception as e:
        logger.exception("get_featured failed")
        return {"items": items, "error": f"{type(e).__name__}: {e}"}


@router.get("/debug")
def debug_selected_file():
    """
    Hızlı teşhis: dosya yolu, var mı yok mu, boyutu, JSON durumu.
    """
    try:
        _ensure_data_dir()

        info: Dict[str, Any] = {
            "save_path": SAVE_PATH,
            "exists": os.path.exists(SAVE_PATH),
            "size_bytes": os.path.getsize(SAVE_PATH) if os.path.exists(SAVE_PATH) else 0,
        }

        if info["exists"]:
            with open(SAVE_PATH, "r", encoding="utf-8") as f:
                raw = f.read()

            info["head"] = raw[:300]
            try:
                data = json.loads(raw) if raw.strip() else {}
                info["json_keys"] = list(data.keys()) if isinstance(data, dict) else "not a dict"
                info["selected_count"] = len(data.get("selected", [])) if isinstance(data, dict) else 0
            except Exception as je:
                info["json_error"] = f"{type(je).__name__}: {je}"

        return info

    except Exception as e:
        logger.exception("debug_selected_file failed")
        return {"debug_error": f"{type(e).__name__}: {e}"}
