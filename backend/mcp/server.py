# backend/mcp/server.py
import os, json, asyncio, websockets, base64
from typing import Dict, Any, List
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Google API
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# ---- Config ----
SCOPES: List[str] = os.getenv(
    "GMAIL_SCOPES",
    "https://www.googleapis.com/auth/gmail.modify https://www.googleapis.com/auth/gmail.send"
).split()

CLIENT_SECRET_FILE = os.environ["GOOGLE_CLIENT_SECRET_FILE"]
TOKEN_FILE = os.environ.get("GOOGLE_TOKEN_FILE", "./data/token.json")

def _ensure_dirs():
    token_dir = os.path.dirname(TOKEN_FILE) or "."
    Path(token_dir).mkdir(parents=True, exist_ok=True)

def _load_creds() -> Credentials | None:
    if os.path.exists(TOKEN_FILE):
        try:
            return Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        except Exception:
            return None
    return None

def _save_creds(creds: Credentials) -> None:
    _ensure_dirs()
    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        f.write(creds.to_json())

def _authorize_if_needed() -> Credentials:
    """
    Desktop app akışı:
    - token varsa ve geçerliyse kullan
    - expired ise refresh et
    - yoksa tarayıcı açıp yeni yetki al
    """
    creds = _load_creds()
    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            _save_creds(creds)
            return creds
        except Exception:
            # refresh başarısızsa sıfırdan yetkilendir
            creds = None

    # İlk kez/yeniden yetkilendirme
    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
    # port=0 → uygun boş portu seçer; tarayıcıyı otomatik açar
    creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")
    _save_creds(creds)
    return creds

def _gmail(creds: Credentials):
    return build("gmail", "v1", credentials=creds, cache_discovery=False)

# ---------- Tools ----------

async def gmail_oauth_url(_: Dict[str, Any]):
    """
    Desktop app'te ayrı bir auth URL üretmeye gerek yok.
    Bu endpoint'i, istemcin hala 'URL istiyorum' diyorsa
    sadece bilgilendirme amacıyla döndürüyoruz.
    """
    return {
        "note": "Desktop flow uses a local browser popup automatically. Call gmail.list_messages or gmail.send to trigger the login."
    }

async def gmail_exchange_code(_: Dict[str, Any]):
    """
    Desktop flow'ta manuel code exchange yok.
    """
    return {"note": "Not required for desktop flow. Authorization happens via local browser automatically."}

async def gmail_list_messages(payload: Dict[str, Any]):
    creds = _authorize_if_needed()
    service = _gmail(creds)

    q = payload.get("q", "newer_than:1d (category:updates OR label:^smartlabel_newsletter)")
    max_results = int(payload.get("max_results", 10))
    resp = service.users().messages().list(userId="me", q=q, maxResults=max_results).execute()
    return {"messages": resp.get("messages", [])}

def _flatten_parts(parts):
    out = []
    for p in parts or []:
        if "parts" in p:
            out.extend(_flatten_parts(p["parts"]))
        else:
            out.append(p)
    return out

async def gmail_get_message(payload: Dict[str, Any]):
    msg_id = payload.get("id")
    if not msg_id:
        return {"error": "missing_id"}

    creds = _authorize_if_needed()
    service = _gmail(creds)
    msg = service.users().messages().get(userId="me", id=msg_id, format="full").execute()

    headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
    parts = _flatten_parts(msg.get("payload", {}).get("parts"))
    b64 = ""
    text_part = next((p for p in parts if p.get("mimeType") == "text/plain"), None)
    html_part = next((p for p in parts if p.get("mimeType") == "text/html"), None)

    if text_part and text_part.get("body", {}).get("data"):
        b64 = text_part["body"]["data"]
    elif html_part and html_part.get("body", {}).get("data"):
        b64 = html_part["body"]["data"]

    content = ""
    if b64:
        # padding sorunlarına karşı güvenli decode
        padding = 4 - (len(b64) % 4)
        if padding and padding < 4:
            b64 += "=" * padding
        content = base64.urlsafe_b64decode(b64.encode()).decode("utf-8", errors="ignore")

    return {
        "id": msg_id,
        "subject": headers.get("Subject", ""),
        "from": headers.get("From", ""),
        "date": headers.get("Date", ""),
        "snippet": msg.get("snippet"),
        "content": content,
    }

async def gmail_send(payload: Dict[str, Any]):
    to = payload.get("to")
    subject = payload.get("subject", "")
    body = payload.get("body")
    html = payload.get("html")
    text = payload.get("text") or payload.get("alt_text") or None

    if not to:
        return {"error": "missing_to"}

    creds = _authorize_if_needed()
    service = _gmail(creds)

    from email.message import EmailMessage
    msg = EmailMessage()
    msg["To"] = to
    msg["Subject"] = subject
    msg["From"] = "me"  # Gmail API 'me' aliasını kabul eder

    if html:
        msg.set_content(text or " ")           # plain text alternatifi
        msg.add_alternative(html, subtype="html")  # HTML part
    else:
        msg.set_content(body or text or "")

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    sent = service.users().messages().send(userId="me", body={"raw": raw}).execute()
    return {"status": "ok", "id": sent.get("id")}


TOOLS = {
    "gmail.oauth_url": gmail_oauth_url,
    "gmail.exchange_code": gmail_exchange_code,
    "gmail.list_messages": gmail_list_messages,
    "gmail.get_message": gmail_get_message,
    "gmail.send": gmail_send,   # <- artık YENİ gmail_send'i işaret ediyor
}


async def handler(ws):
    async for raw in ws:
        try:
            data = json.loads(raw)
        except Exception:
            await ws.send(json.dumps({"error": "invalid_json"}))
            continue

        t = data.get("type")
        payload = data.get("payload", {}) or {}

        if t == "connect":
            await ws.send(json.dumps({"type": "connected", "agent": data.get("agent_name")}))
            continue

        fn = TOOLS.get(t)
        if not fn:
            await ws.send(json.dumps({"error": "unknown_type", "type": t}))
            continue

        try:
            res = await fn(payload)
            await ws.send(json.dumps({"type": f"{t}.result", "result": res}))
        except Exception as e:
            await ws.send(json.dumps({"type": f"{t}.error", "error": str(e)}))

async def main():
    port = int(os.environ.get("MCP_PORT", "8080"))
    async with websockets.serve(handler, "0.0.0.0", port):
        print(f"✅ MCP listening ws://localhost:{port}")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
