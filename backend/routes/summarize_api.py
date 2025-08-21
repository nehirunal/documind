from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.summarizer.summarizer import summarize_text_with_openai

router = APIRouter(prefix="/api", tags=["summarize"])

class SummarizeBody(BaseModel):
    text: str
    lang: str | None = None

@router.post("/summarize")
def summarize(body: SummarizeBody):
    txt = (body.text or "").strip()
    if not txt:
        raise HTTPException(400, "text boş")
    out = summarize_text_with_openai(txt, lang=body.lang)
    return {"summary": out}
