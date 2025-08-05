# backend/agents/email_agent.py
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from dotenv import load_dotenv
from backend.utils.rss_reader import get_latest_headlines
from backend.email_utils.mail_sender import send_email_from_documind

from langchain.chat_models import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage

# Ortam değişkenlerini yükle
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

# LangChain LLM nesnesi
llm = ChatOpenAI(model="gpt-3.5-turbo", api_key=api_key)

# Abone listesi yolu
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SUBSCRIBERS_FILE = os.path.join(BASE_DIR, "data", "subscribers.txt")


def summarize_from_rss(limit: int = 5) -> str:
    """RSS kaynaklı haberleri özetle"""
    try:
        headlines = get_latest_headlines("https://www.ntv.com.tr/turkiye.rss", limit=limit)
        print("📰 Başlıklar:\n", headlines)

        prompt = (
            "Aşağıda haber başlıkları ve linkleri verilmiştir.\n"
            "Her başlık için bir satırlık Türkçe özet yaz. Format:\n"
            "📰 <Başlık>\n<Açıklama>\n\n"
            "İçerikler:\n"
            f"{headlines}"
        )

        response = llm([
            SystemMessage(content="Sen haberleri özetleyen bir asistansın."),
            HumanMessage(content=prompt)
        ])
        
        summary = response.content.strip()
        print("📝 Üretilen Özet:\n", summary)
        return summary

    except Exception as e:
        print("❌ Özetleme hatası:", e)
        raise


def summarize_and_send():
    """Test amaçlı tek kişiye özet gönder."""
    try:
        summary = summarize_from_rss(limit=5)
        send_email_from_documind(
            receiver_email="nehiru789@gmail.com",
            subject="🗞️ Günlük Haber Özeti",
            body=summary,
        )
        print("✅ Mail gönderildi: nehiru789@gmail.com")
    except Exception as e:
        print("❌ Mail gönderilemedi:", e)
        raise


def send_daily_news_to_all():
    """Tüm abonelere günlük özet gönder."""
    try:
        if not os.path.exists(SUBSCRIBERS_FILE):
            print(f"❗ Abone dosyası bulunamadı: {SUBSCRIBERS_FILE}")
            return

        with open(SUBSCRIBERS_FILE, "r") as f:
            emails = [line.strip() for line in f if line.strip()]

        if not emails:
            print("🚫 Gönderilecek abone yok.")
            return

        summary = summarize_from_rss(limit=5)
        for email in emails:
            try:
                send_email_from_documind(
                    receiver_email=email,
                    subject="🗞️ Günlük Haber Özeti",
                    body=summary,
                )
                print(f"✅ Gönderildi: {email}")
            except Exception as e:
                print(f"❌ Gönderilemedi ({email}):", e)
    except Exception as e:
        print("❌ Genel hata:", e)
        raise


if __name__ == "__main__":
    # Test etmek istersen aşağıyı aç
    # summarize_and_send()
    send_daily_news_to_all()
