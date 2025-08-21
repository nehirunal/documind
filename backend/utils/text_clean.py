# backend/utils/text_clean.py
import re
from bs4 import BeautifulSoup

_UNSUB_PATTERNS = [
    "unsubscribe",
    "view email in browser",
    "view in browser",
    "privacy policy",
    "manage preferences",
    "update preferences",
    "contact us",
    "sponsored",
    "in partnership with",
    "advertiser content",
    "ad:",
    "sponsor:",
    "read in browser",
    "read on the web",
    "open in browser",
]

# “tarih/başlık/abone” gibi çöp satırları erkenden at
_HEADER_GARBAGE_RE = re.compile(
    r"""(?imx)
    ^\s*(subscribe|read\s+in\s+browser|view\s+in\s+browser)\b.*?$|
    ^\s*(editor'?s\s+note)\b.*?$|
    ^\s*(aug|sep|oct|nov|dec|jan|feb|mar|apr|may|jun|jul)\w*\s+\d{1,2},\s+\d{4}.*?$|
    ^\s*(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b.*?$
    """,
)

_URL_RE = re.compile(r"http[s]?://\S+", re.I)

def _strip_unsub_blocks(soup: BeautifulSoup):
    for t in soup(["script", "style", "noscript"]):
        t.decompose()

    # metin düğümlerini tarayıp üst bloğu kaldır
    for el in list(soup.find_all(string=True)):
        s = (el or "").strip().lower()
        if not s:
            continue
        if any(p in s for p in _UNSUB_PATTERNS):
            p = el.parent
            if p and p.name not in ("body", "html"):
                p.decompose()

def clean_text(html_or_text: str) -> str:
    """
    Newsletter gövdesini temizler:
    - HTML ise <script/style> ve typik footer/CTA/unsub bloklarını siler,
    - 'read in browser', tarih başlıkları, fazla URL ve boşlukları kırpar,
    - gereksiz satırları ayıklar.
    """
    if not html_or_text:
        return ""

    # HTML ise parse et
    if "<" in html_or_text and ">" in html_or_text:
        soup = BeautifulSoup(html_or_text, "html.parser")
        _strip_unsub_blocks(soup)
        text = soup.get_text("\n", strip=True)
    else:
        text = html_or_text

    # header/çöp satırlarını temizle
    lines = [ln for ln in text.splitlines() if ln.strip()]
    lines = [ln for ln in lines if not _HEADER_GARBAGE_RE.search(ln)]
    text = "\n".join(lines)

    # URL'leri ayıkla (takip parametrelerini ve raw linkleri)
    text = _URL_RE.sub("", text)

    # aşırı boşlukları toparla
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
