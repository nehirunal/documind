import requests
from bs4 import BeautifulSoup
from transformers import pipeline
import tempfile
import fitz  # PyMuPDF

# Model önceden yüklenir
summarizer = pipeline("summarization", model="facebook/bart-large-cnn")

def summarize_url(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    paragraphs = " ".join([p.text for p in soup.find_all('p')][:10])
    summary = summarizer(paragraphs, max_length=100, min_length=30, do_sample=False)
    return summary[0]['summary_text']

def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(pdf_bytes)
        tmp_path = tmp.name

    doc = fitz.open(tmp_path)
    text = "\n".join(page.get_text() for page in doc)
    doc.close()
    return text

def summarize_file(file_bytes, filename):
    text = extract_text_from_pdf(file_bytes)

    # Parçalama
    chunks = [text[i:i+1000] for i in range(0, len(text), 1000)]
    summaries = []

    for chunk in chunks:
        if len(chunk.strip()) > 100:
            result = summarizer(chunk, max_length=300, min_length=50, do_sample=False)
            summaries.append(result[0]["summary_text"])

    return "\n\n".join(summaries)
