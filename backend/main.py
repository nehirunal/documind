# backend/main.py
import os
from datetime import datetime,  timedelta
from pathlib import Path
from typing import List, Optional

from zoneinfo import ZoneInfo
from fastapi import APIRouter, Query

from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).parent / ".env")

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr

from backend.config.database import Base, engine as sa_engine
from sqlmodel import SQLModel, Field, Session, select
from .routes import newsletters
from backend.routes.summarize_api import router as summarize_router

app = FastAPI(title="Newsly Backend", debug=True)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routerlar – SADECE BURADA include et
from backend.routes import auth
from backend.routes.newsletters import router as newsletters_router
app.include_router(auth.router)
app.include_router(newsletters.router)
app.include_router(summarize_router)
app.include_router(auth.router, prefix="/api")




# SQLModel tablo
class Newsletter(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    gmail_id: str = Field(index=True)
    subject: str
    sender: str
    body: str
    category: Optional[str] = Field(default=None, index=True)
    received_at: Optional[str] = None

# ENV
NEWSLY_API_KEY = os.getenv("NEWSLY_API_KEY", "dev-key")
USER_EMAIL = os.getenv("USER_EMAIL", "nehiru789@gmail.com")
NEWSLY_GMAIL_QUERY = os.getenv(
    "NEWSLY_GMAIL_QUERY",
    'in:anywhere newer_than:30d from:me subject:"[SEED]" -subject:"[GMAIL]"'
)

from backend.summarizer.summarizer import summarize_file, summarize_url, summarize_text_with_openai
from backend.agents.email_agent import gmail_send, summarize_gmail_and_send

@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=sa_engine)
    SQLModel.metadata.create_all(sa_engine)

@app.post("/summarize")
async def summarize_api(
    file: UploadFile = File(None),
    content: str = Form(None),
    url: str = Form(None)
):
    try:
        if file:
            file_bytes = await file.read()
            return {"summary": summarize_file(file_bytes, file.filename)}
        elif url:
            return {"summary": summarize_url(url)}
        elif content:
            return {"summary": summarize_text_with_openai(content)}
        else:
            raise HTTPException(status_code=400, detail="No content, file or url provided.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/send-email")
async def send_email_api(
    receiver_email: str = Form(...),
    subject: str = Form(...),
    message: str = Form(...)
):
    try:
        await gmail_send(receiver_email, subject, message)
        return {"status": "E-posta başarıyla gönderildi (Gmail API/MCP)"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def _auth(x_api_key: str = Header(None)):
    if not x_api_key or x_api_key != NEWSLY_API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

class NewsletterIn(BaseModel):
    gmail_id: str
    subject: str
    sender: str
    body: str
    category: Optional[str] = None
    received_at: Optional[str] = None

class ImportPayload(BaseModel):
    user_email: EmailStr
    items: List[NewsletterIn]

@app.post("/newsletters/import")
async def import_newsletters(payload: ImportPayload, x_api_key: str = Header(None)):
    _auth(x_api_key)
    try:
        with Session(sa_engine) as s:
            inserted = 0
            for it in payload.items:
                exists = s.exec(select(Newsletter).where(Newsletter.gmail_id == it.gmail_id)).first()
                if exists:
                    exists.subject = it.subject
                    exists.sender = it.sender
                    exists.body = it.body
                    exists.category = it.category
                    exists.received_at = it.received_at
                else:
                    s.add(Newsletter(
                        gmail_id=it.gmail_id,
                        subject=it.subject,
                        sender=it.sender,
                        body=it.body,
                        category=it.category,
                        received_at=it.received_at or datetime.utcnow().isoformat()
                    ))
                    inserted += 1
            s.commit()
        return {"status": "ok", "inserted": inserted}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/newsletters")
async def list_newsletters(category: Optional[str] = None, q: Optional[str] = None, limit: int = 50):
    try:
        with Session(sa_engine) as s:
            stmt = select(Newsletter).order_by(Newsletter.id.desc()).limit(limit)
            if category:
                stmt = stmt.where(Newsletter.category == category)
            rows = s.exec(stmt).all()
        if q:
            rows = [r for r in rows if (q.lower() in r.subject.lower()) or (q.lower() in (r.body or "").lower())]
        return [{
            "id": r.id,
            "gmail_id": r.gmail_id,
            "subject": r.subject,
            "sender": r.sender,
            "body": r.body,
            "category": r.category,
            "received_at": r.received_at
        } for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

SUBSCRIBERS_FILE = os.path.join(os.path.dirname(__file__), "data", "subscribers.txt")

@app.post("/subscribe-news")
async def subscribe_news(request: Request):
    form = await request.form()
    email = form.get("email")
    if not email or not email.strip():
        raise HTTPException(status_code=400, detail="Email gerekli")
    os.makedirs(os.path.dirname(SUBSCRIBERS_FILE), exist_ok=True)
    with open(SUBSCRIBERS_FILE, "a") as f:
        f.write(email.strip() + "\n")
    return {"status": "Başarıyla abone oldunuz"}

@app.get("/run-agent")
async def run_agent():
    try:
        result = await summarize_gmail_and_send(
            target_email=USER_EMAIL,
            limit=10,
            query=NEWSLY_GMAIL_QUERY
        )
        return {"status": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")


