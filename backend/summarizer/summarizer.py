# backend/summarizer/summarizer.py
from __future__ import annotations

import os
import json
import tempfile
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI
import requests
from bs4 import BeautifulSoup
import fitz  # PyMuPDF
import requests as rq

# ---- OpenAI client & config ----
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")           # kalite için: o4-mini / gpt-4o
TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0.2"))  # daha tutarlı özetler için düşük
SUMMARY_LANG = os.getenv("SUMMARY_LANG", "tr").lower()       # 'tr' ya da 'en'
PROXY_URL = os.getenv("SUMMARY_PROXY_URL")  # senin host ettiğin URL: https://<senin-url>/api/summarize


# ---- Low-level helper: safe chat completion ----
def _chat(messages: List[Dict[str, str]], max_tokens: int = 400) -> str:
    """
    OpenAI ChatCompletion çağrısını güvenli şekilde yapar ve metni döner.
    """
    resp = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=TEMPERATURE,
        max_tokens=max_tokens,
    )
    return (resp.choices[0].message.content or "").strip()


# ---- 1) Kısa, 2-3 cümlelik özet ----
def summarize_text_with_openai(text: str, lang: Optional[str] = None) -> str:
    """
    Verilen metni GPT ile 2-3 cümlede özetler (dil varsayılanı .env SUMMARY_LANG).
    """
    if not text or not text.strip():
        return "Metin boş görünüyor."

    _lang = (lang or SUMMARY_LANG).lower()
    system = (
        "Sen bir içerik özetleyicisisin. Metni kısa, net ve anlamlı biçimde 2-3 cümleyle özetle."
        if _lang.startswith("tr")
        else "You are a concise content summarizer. Summarize the text in 2-3 clear sentences in English."
    )

    try:
        return _chat(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": text},
            ],
            max_tokens=300,
        )
    except Exception as e:
        return f"OpenAI özetleme hatası: {e}"


# ---- 2) Newsletter tarzı zengin özet: başlık + 5 madde + TL;DR ----
def summarize_newsletter(content: str, sender: str = "", date_iso: str = "", lang: Optional[str] = None) -> Dict[str, Any]:
    """
    DÖNÜŞ:
    {
      "title": "...",
      "bullets": ["...", "...", "...", "...", "..."],
      "tldr": "..."
    }
    """
    if not content or not content.strip():
        return {"title": sender or "Bülten", "bullets": [], "tldr": ""}

    _lang = (lang or SUMMARY_LANG).lower()
    system = (
        "Kısa ve vurucu bir bülten editörüsün."
        if _lang.startswith("tr")
        else "You are a concise newsletter editor. Output in English."
    )

    prompt = f"""
Kaynak gönderici: {sender or '-'}
Tarih (ISO): {date_iso or '-'}

Metin aşağıda. Görevlerin:
1) 6-10 kelimelik vurucu bir başlık yaz .
2) En fazla 5 madde: her madde tek cümle, bilgi yoğun, gereksiz laf yok.
3) En sonda tek cümlelik kısa TL;DR.
4) Link reklamları, “unsubscribe” vb. kısımları dışarıda bırak.
5) Varsa sayısal veri, tarih, metrik ve özel isimleri koru.

ÇIKTIYI SADECE AŞAĞIDAKİ GİBİ GEÇERLİ JSON OLARAK DÖN:
{{
  "title": "...",
  "bullets": ["...", "...", "...", "...", "..."],
  "tldr": "..."
}}

METİN:
\"\"\"{content[:8000]}\"\"\"
"""

    try:
        text = _chat(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            max_tokens=600,
        )

        data = json.loads(text)
        if not isinstance(data, dict):
            raise ValueError("Model JSON yerine farklı çıktı verdi")

    except Exception:
        # Güvenli yedek: kısa özet üretip tek madde gibi dön
        short = summarize_text_with_openai(content, lang=_lang)
        data = {
            "title": sender or "Bülten",
            "bullets": [short] if short else [],
            "tldr": short,
        }

    # Normalizasyon
    data.setdefault("title", sender or "Bülten")
    bullets = data.get("bullets") or []
    if isinstance(bullets, list):
        data["bullets"] = [str(b).strip() for b in bullets if b] [:5]
    else:
        data["bullets"] = [str(bullets).strip()]

    data["tldr"] = (data.get("tldr") or "").strip()
    return data


# ---- 3) URL özetleme (basit <p> toplayıcı) ----
def summarize_url(url: str, lang: Optional[str] = None) -> str:
    """
    URL'den içerik çekip özetleme yapar (basit HTML <p> toplayıcı).
    """
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    paragraphs = " ".join([p.get_text(" ", strip=True) for p in soup.find_all("p")][:10])
    return summarize_text_with_openai(paragraphs or f"Bu sayfa için özet üret: {url}", lang=lang)


# ---- 4) PDF'ten metin çıkarma ----
def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """
    PDF içeriğini düz metne çevirir (PyMuPDF).
    """
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(pdf_bytes)
        tmp_path = tmp.name

    doc = fitz.open(tmp_path)
    try:
        text = "\n".join(page.get_text() for page in doc)
    finally:
        doc.close()
    return text


# ---- 5) Dosya özetleme (PDF) ----
def summarize_file(file_bytes: bytes, filename: str, lang: Optional[str] = None) -> str:
    """
    PDF dosyasını özetler (uzunsa parça parça).
    """
    text = extract_text_from_pdf(file_bytes)
    if not text or len(text.strip()) < 50:
        return "PDF içeriği okunamadı ya da çok kısa görünüyor."

    # Basit parçalama (token yerine karakter bazlı; hızlı ve pratik)
    chunks = [text[i:i + 2000] for i in range(0, len(text), 2000)]
    summaries: List[str] = []
    for chunk in chunks:
        if len(chunk.strip()) > 100:
            summaries.append(summarize_text_with_openai(chunk, lang=lang))

    if summaries:
        # Parça özetlerini tek kısa paragrafa indir
        joined = "\n\n".join(summaries)
        return summarize_text_with_openai(joined, lang=lang)

    return summarize_text_with_openai(text[:2000], lang=lang)


# --- EKLE: Kart + modal için iki seviyeli özet ---
def summarize_newsletter_tiered(content: str, sender: str = "", date_iso: str = "") -> Dict[str, str]:
    """
    ÇIKTI (kaynak dilini KORUYARAK):
    {
      "title": "...",
      "teaser": "3-4 punchy cümle",
      "long": "15-20 cümlelik ayrıntılı özet"
    }
    """
    if not content or not content.strip():
        return {"title": sender or "Newsletter", "teaser": "", "long": ""}

    system = (
        "You are a sharp newsletter editor. IMPORTANT: Detect and KEEP the source language exactly; DO NOT translate."
        " Do not add ads, unsubscribes, or tracking fluff."
    )

    prompt = f"""
Source: {sender or '-'}
Date: {date_iso or '-'}

Write output in the SAME language as the source text. DO NOT translate.

Tasks:
1) Produce a short catchy title (6–12 words).
2) Write a TEASER: 3–4 punchy sentences that capture the most impactful insights across different subtopics. No bullets.
3) Write a LONG SUMMARY: 15–20 full sentences, logically structured, cohesive, no repetition, no lists; keep numbers, entities, dates.

Return STRICT JSON only:
{{
  "title": "...",
  "teaser": "...",
  "long": "..."
}}

TEXT:
\"\"\"{content[:9000]}\"\"\"
"""

    try:
        text = _chat(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            max_tokens=1200,
        )
        data = json.loads(text)
        if not isinstance(data, dict):
            raise ValueError("not a dict")
    except Exception:
        # emniyet: tek aşamalı kısa özet
        short = summarize_text_with_openai(content, lang=None)
        data = {"title": sender or "Newsletter", "teaser": short, "long": short}

    # normalize
    out = {
        "title": (data.get("title") or sender or "Newsletter").strip(),
        "teaser": (data.get("teaser") or "").strip(),
        "long": (data.get("long") or "").strip(),
    }
    return out


def summarize_text_with_openai(text: str, lang: Optional[str] = None) -> str:
    if PROXY_URL and not os.getenv("OPENAI_API_KEY"):
        try:
            r = rq.post(PROXY_URL, json={"text": text, "lang": lang}, timeout=30)
            r.raise_for_status()
            return (r.json() or {}).get("summary","")
        except Exception as e:
            return f"Proxy summarize hatası: {e}"