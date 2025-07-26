from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from summarizer import summarize_pdf

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Geliştirme için geçici olarak * kullan
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/summarize")
async def summarize(file: UploadFile = File(...)):
    content = await file.read()
    summary = summarize_pdf(content)
    return {"summary": summary}
