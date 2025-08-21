# backend/utils/gmail_client.py
from __future__ import annotations
import os, glob
from typing import List, Optional
from pathlib import Path
from typing import Tuple
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from backend.config.paths import CREDENTIALS_PATH, TOKEN_PATH

SECRETS_FILE = os.environ["GOOGLE_CLIENT_SECRETS_FILE"]
TOKEN_FILE = os.getenv("GOOGLE_TOKEN_FILE", "./data/token.json")
SCOPES = os.getenv("GMAIL_SCOPES", "https://www.googleapis.com/auth/gmail.readonly").split()


def get_gmail_service():
    Path(os.path.dirname(TOKEN_FILE)).mkdir(parents=True, exist_ok=True)

    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    # Token yoksa veya kapsamlar değiştiyse yeniden yetkilendir
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())  # type: ignore
            except Exception:
                creds = None
        if not creds:
            flow = InstalledAppFlow.from_client_secrets_file(SECRETS_FILE, SCOPES)
            # Desktop app akışı: tarayıcıyı açar, localhost loopback ile döner
            creds = flow.run_local_server(port=0)  # uygun boş portu seçer
        # token'ı kaydet
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    service = build("gmail", "v1", credentials=creds)
    return service

def list_last_messages(max_results: int = 5) -> list:
    service = get_gmail_service()
    resp = service.users().messages().list(userId="me", maxResults=max_results).execute()
    return resp.get("messages", [])

def _find_client_secret_path() -> str:
    here = os.path.dirname(__file__)
    matches = glob.glob(os.path.join(here, "client_secret*.json"))
    if not matches:
        raise FileNotFoundError("utils/ içinde client_secret*.json bulunamadı.")
    return matches[0]

def _ensure_creds() -> Credentials:
    creds: Optional[Credentials] = None

    # token.json varsa yükle
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    # token yoksa veya yenilenmesi gerekiyorsa akışı başlat
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_PATH):
                raise FileNotFoundError(f"credentials.json bulunamadı: {CREDENTIALS_PATH}")
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            # İlk seferde tarayıcı açılır, izin verirsin
            creds = flow.run_local_server(port=0)

        # token kaydet
        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())

    return creds



