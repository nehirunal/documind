import fitz  # PyMuPDF
from transformers import pipeline
import tempfile

def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(pdf_bytes)
        tmp_path = tmp.name

    doc = fitz.open(tmp_path)
    text = "\n".join(page.get_text() for page in doc)
    doc.close()
    return text

def summarize_pdf(pdf_bytes: bytes) -> str:
    text = extract_text_from_pdf(pdf_bytes)
    summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
    chunks = [text[i:i+1000] for i in range(0, len(text), 1000)]
    summaries = [
        summarizer(chunk, max_length=300, min_length=50, do_sample=False)[0]["summary_text"]
        for chunk in chunks if len(chunk.strip()) > 100
    ]
    return "\n\n".join(summaries)
