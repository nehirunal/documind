import os, re
from typing import Dict, Any
from openai import OpenAI

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")  # senin dediğin mini
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM = (
    "You extract a compact TOPIC LABEL for a newsletter. "
    "Return ONLY 1–2 words, Title Case, no punctuation, no emojis. "
    "Examples: 'Trump', 'OpenAI', 'US Politics', 'Instagram', 'AI Policy'."
)

def _fallback_label(subject: str, body: str) -> str:
    # Basit yedek: subject içinden özel isim/marka yakala
    text = subject.strip() or body[:200]
    # Büyük harfle başlayan kelimeler
    cands = re.findall(r"\b([A-ZÇĞİÖŞÜ][A-Za-zÇĞİÖŞÜçğıöşü0-9\-]{2,})\b", text)
    if cands:
        # İlk 1–2 kelimeyi al
        return " ".join(cands[:2])[:30].title()
    # Hiçbir şey yoksa:
    return "General"

def label_newsletter(subject: str, body: str) -> str:
    text = f"SUBJECT: {subject}\n\nBODY:\n{body[:6000]}"
    try:
        resp = client.responses.create(
            model=OPENAI_MODEL,
            input=[
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": text},
            ],
            temperature=0.2,
        )
        # Yeni Responses API: düz metni güvenli çek
        out = resp.output_text.strip()
        # Normalize: sadece harf/rakam/boşluk
        out = re.sub(r"[^A-Za-z0-9ÇĞİÖŞÜçğıöşü\s\-]", "", out).strip()
        # En fazla 2 kelime
        words = out.split()
        if not words:
            return _fallback_label(subject, body)
        label = " ".join(words[:2])
        # Title Case
        return label.title()[:30]
    except Exception:
        return _fallback_label(subject, body)
