# backend/main.py

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from summarizer.summarizer import summarize_file, summarize_url
from chat.chat_bot import ask_question_with_pdf
from email_utils.mail_sender import send_email_from_documind
from agents.email_agent import summarize_and_send

import os
from uuid import uuid4

app = FastAPI()

# CORS ayarları
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Güvenlik için prod'da sınırlayın
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Yükleme klasörü
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# 🔹 PDF dosyasından özetleme ve isteğe bağlı e-posta gönderimi
@app.post("/summarize")
async def summarize_file_api(
    file: UploadFile = File(...),
    email: str = Form(None)  # opsiyonel olarak e-posta parametresi alır
):
    try:
        content = await file.read()
        summary = summarize_file(content, file.filename)

        # Eğer kullanıcı e-posta girdiyse gönder
        if email:
            subject = "📄 Belge Özeti"
            send_email_from_documind(email, subject, summary)

        return {"summary": summary}
    except Exception as e:
        return {"error": str(e)}

# 🔹 URL'den özetleme
@app.post("/summarize-url")
async def summarize_url_api(url: str = Form(...)):
    try:
        summary = summarize_url(url)
        return {"summary": summary}
    except Exception as e:
        return {"error": str(e)}

# 🔹 PDF dosyasına göre soruya yanıt
@app.post("/chat-with-pdf")
async def chat_with_pdf(file: UploadFile = File(...), question: str = Form(...)):
    temp_filename = f"{uuid4().hex}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, temp_filename)

    try:
        with open(file_path, "wb") as f:
            f.write(await file.read())

        response = ask_question_with_pdf(file_path, question)
        return {"answer": response}

    except Exception as e:
        return {"error": str(e)}

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

# 🔹 Manuel e-posta gönderme endpoint’i
@app.post("/send-email")
async def send_email_api(
    receiver_email: str = Form(...),
    subject: str = Form(...),
    message: str = Form(...)
):
    try:
        send_email_from_documind(receiver_email, subject, message)
        return {"status": "E-posta başarıyla gönderildi"}
    except Exception as e:
        return {"error": str(e)}
    
SUBSCRIBERS_FILE = os.path.join(os.path.dirname(__file__), "backend", "data", "subscribers.txt")

@app.post("/subscribe-news")
async def subscribe_news(request: Request):
    form = await request.form()
    email = form.get("email")

    if not email or not email.strip():
        raise HTTPException(status_code=400, detail="Email gerekli")

    os.makedirs(os.path.dirname(SUBSCRIBERS_FILE), exist_ok=True)  # klasör yoksa oluştur
    with open(SUBSCRIBERS_FILE, "a") as f:
        f.write(email.strip() + "\n")

    return {"status": "Başarıyla abone oldunuz"}


@app.get("/run-agent")
def run_agent():
    try:
        summarize_and_send()
        return {"status": "Başarıyla özetlendi ve e-posta gönderildi."}
    except Exception as e:
        return {"error": str(e)}
    
@app.get("/send-to-all")
def trigger_news_email():
    try:
        send_daily_news_to_all()
        return {"status": "Tüm abonelere gönderildi"}
    except Exception as e:
        return {"error": str(e)}    
    
